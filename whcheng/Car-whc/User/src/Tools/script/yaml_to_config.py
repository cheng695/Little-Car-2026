#!/usr/bin/env python3
"""Generate C++ robot config from a Little-Car YAML file.

This script intentionally supports only the YAML subset used by configs/*.yaml:
nested maps, scalar values, simple lists, and inline maps such as
{ timer: htim1, channel: TIM_CHANNEL_3 }.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / "configs" / "little_car_2026.yaml"
DEFAULT_OUTPUT = ROOT / "src" / "Tools" / "generated" / "robot_config.hpp"
DEFAULT_MESSAGES_OUTPUT = ROOT / "src" / "Tools" / "generated" / "robot_messages.hpp"
DEFAULT_RUNTIME_OUTPUT = ROOT / "src" / "Tools" / "generated" / "robot_runtime.hpp"

SUPPORTED_MESSAGE_TYPES = {
    "bool",
    "float",
    "double",
    "int8_t",
    "uint8_t",
    "int16_t",
    "uint16_t",
    "int32_t",
    "uint32_t",
    "int64_t",
    "uint64_t",
}


class ConfigError(RuntimeError):
    pass


def strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


def parse_scalar(value: str):
    value = value.strip()
    if value == "":
        return {}
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if value in ("null", "None", "~"):
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.startswith("{") and value.endswith("}"):
        return parse_inline_map(value)
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?(\d+\.\d*|\d*\.\d+|\d+)([eE][-+]?\d+)?", value):
        return float(value)
    return value


def split_inline_items(body: str) -> list[str]:
    items = []
    token = []
    in_single = False
    in_double = False
    for ch in body:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double

        if ch == "," and not in_single and not in_double:
            item = "".join(token).strip()
            if item:
                items.append(item)
            token = []
        else:
            token.append(ch)
    item = "".join(token).strip()
    if item:
        items.append(item)
    return items


def parse_inline_map(value: str) -> dict:
    result = {}
    body = value.strip()[1:-1].strip()
    if not body:
        return result
    for item in split_inline_items(body):
        if ":" not in item:
            raise ConfigError(f"Invalid inline map item: {item}")
        key, raw_value = item.split(":", 1)
        result[key.strip()] = parse_scalar(raw_value)
    return result


def load_yaml_subset(path: Path) -> dict:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = []
    for line_no, raw in enumerate(raw_lines, 1):
        stripped = strip_comment(raw).rstrip()
        if stripped.strip() == "":
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        if indent % 2 != 0:
            raise ConfigError(f"{path}:{line_no}: indentation must use 2 spaces")
        lines.append((line_no, indent, stripped.lstrip(" ")))

    root = {}
    stack = [(-1, root)]

    for index, (line_no, indent, text) in enumerate(lines):
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ConfigError(f"{path}:{line_no}: invalid indentation")

        parent = stack[-1][1]
        if text.startswith("- "):
            if not isinstance(parent, list):
                raise ConfigError(f"{path}:{line_no}: list item without list parent")
            parent.append(parse_scalar(text[2:]))
            continue

        if ":" not in text:
            raise ConfigError(f"{path}:{line_no}: expected key: value")

        key, raw_value = text.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if raw_value == "":
            next_is_list = False
            if index + 1 < len(lines):
                _, next_indent, next_text = lines[index + 1]
                next_is_list = next_indent > indent and next_text.startswith("- ")

            container = [] if next_is_list else {}
            parent[key] = container
            stack.append((indent, container))
        else:
            parent[key] = parse_scalar(raw_value)

    return root


def walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_dicts(value)


def require(mapping: dict, key: str, path: str):
    if key not in mapping:
        raise ConfigError(f"Missing required field: {path}.{key}")
    return mapping[key]


def as_float(value) -> float:
    if not isinstance(value, (int, float)):
        raise ConfigError(f"Expected number, got {value!r}")
    return float(value)


def as_int(value) -> int:
    if not isinstance(value, int):
        raise ConfigError(f"Expected integer, got {value!r}")
    return value


def cpp_string(value) -> str:
    text = "" if value is None else str(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def cpp_float(value) -> str:
    text = f"{as_float(value):.9g}"
    if "." not in text and "e" not in text and "E" not in text:
        text += ".0"
    return f"{text}f"


def cpp_bool(value) -> str:
    return "true" if bool(value) else "false"


def to_identifier(name: str) -> str:
    parts = re.split(r"[^0-9A-Za-z]+", name)
    text = "".join(part[:1].upper() + part[1:] for part in parts if part)
    if not text:
        raise ConfigError(f"Cannot build identifier from {name!r}")
    if text[0].isdigit():
        text = "_" + text
    return text


def to_field_identifier(name: str) -> str:
    text = re.sub(r"[^0-9A-Za-z_]", "_", name).strip("_")
    if not text:
        raise ConfigError(f"Cannot build field identifier from {name!r}")
    if text[0].isdigit():
        text = "_" + text
    return text


def cpp_message_type(value) -> str:
    text = str(value)
    if text not in SUPPORTED_MESSAGE_TYPES:
        raise ConfigError(f"Unsupported message field type: {text}")
    return text


def cpp_symbol(value) -> str:
    text = str(value)
    if not re.fullmatch(r"[A-Za-z_][0-9A-Za-z_]*", text):
        raise ConfigError(f"Expected C++ symbol, got {text!r}")
    return text


def validate_config(config: dict) -> None:
    robot = require(config, "robot", "config")
    require(robot, "name", "robot")
    require(robot, "target", "robot")
    chassis_type = require(robot, "chassis_type", "robot")
    if chassis_type != "differential_drive":
        raise ConfigError(f"Unsupported chassis_type: {chassis_type}")

    control = require(config, "control", "config")
    chassis_ik = require(control, "chassis_ik", "control")
    if require(chassis_ik, "type", "control.chassis_ik") != "differential_drive":
        raise ConfigError("Only differential_drive chassis_ik is supported")
    ik_config = require(chassis_ik, "config", "control.chassis_ik")
    require(ik_config, "wheel_radius_m", "control.chassis_ik.config")
    require(ik_config, "half_track_m", "control.chassis_ik.config")

    pid_map = require(control, "pid", "control")
    hardware = require(config, "hardware", "config")
    motors = require(hardware, "motors", "hardware")
    encoders = require(hardware, "encoders", "hardware")
    messages = config.get("messages", {})

    seen_indexes = set()
    for name, motor in motors.items():
        index = as_int(require(motor, "ik_index", f"hardware.motors.{name}"))
        if index < 0 or index > 3:
            raise ConfigError(f"hardware.motors.{name}.ik_index must be 0..3")
        if index in seen_indexes:
            raise ConfigError(f"Duplicated ik_index: {index}")
        seen_indexes.add(index)

        pid_name = require(motor, "speed_pid", f"hardware.motors.{name}")
        if pid_name not in pid_map:
            raise ConfigError(f"Motor {name} references missing PID {pid_name}")

        encoder_name = require(motor, "encoder", f"hardware.motors.{name}")
        if encoder_name not in encoders:
            raise ConfigError(f"Motor {name} references missing encoder {encoder_name}")

        require(motor, "reduction_ratio", f"hardware.motors.{name}")

    if seen_indexes != {0, 1, 2, 3}:
        raise ConfigError("Motors must define ik_index 0, 1, 2, and 3")

    for name, pid in pid_map.items():
        for field in ("kp", "ki", "kd", "output_limit", "integral_limit", "T"):
            require(pid, field, f"control.pid.{name}")

    for name, encoder in encoders.items():
        cpr = as_int(require(encoder, "cpr", f"hardware.encoders.{name}"))
        if cpr <= 0:
            raise ConfigError(f"hardware.encoders.{name}.cpr must be positive")

    for name, message in messages.items():
        fields = require(message, "fields", f"messages.{name}")
        if not isinstance(fields, dict) or not fields:
            raise ConfigError(f"messages.{name}.fields must be a non-empty map")
        for field_name, field_type in fields.items():
            to_field_identifier(field_name)
            cpp_message_type(field_type)

        subscribers = message.get("subscribers", [])
        if not isinstance(subscribers, list):
            raise ConfigError(f"messages.{name}.subscribers must be a list")
        if len(subscribers) > 4:
            raise ConfigError(f"Message {name} has more than 4 subscribers")


def generate_header(config: dict, source_path: Path) -> str:
    robot = config["robot"]
    control = config["control"]
    ik_config = control["chassis_ik"]["config"]
    pid_map = control["pid"]
    hardware = config["hardware"]
    motors = hardware["motors"]
    encoders = hardware["encoders"]
    uart_map = config.get("communication", {}).get("uart", {})
    messages = config.get("messages", {})

    lines = []
    lines.append("// Generated by src/Tools/script/yaml_to_config.py.")
    lines.append(f"// Source: {source_path.as_posix()}")
    lines.append("#ifndef ROBOT_CONFIG_HPP")
    lines.append("#define ROBOT_CONFIG_HPP")
    lines.append("")
    lines.append("#include <stdint.h>")
    lines.append("")
    lines.append('#include "CalculationBase.hpp"')
    lines.append('#include "pid.hpp"')
    lines.append("")
    lines.append("namespace RobotConfig")
    lines.append("{")
    lines.append(f"    static constexpr const char *kRobotName = {cpp_string(robot['name'])};")
    lines.append(f"    static constexpr const char *kRobotTarget = {cpp_string(robot['target'])};")
    lines.append(
        f"    static constexpr const char *kChassisType = {cpp_string(robot['chassis_type'])};"
    )
    lines.append("")
    lines.append(
        "    static constexpr ALG::ChassisIK::ChassisIKConfig kChassisIKConfig = "
        f"{{{cpp_float(ik_config['wheel_radius_m'])}, {cpp_float(ik_config['half_track_m'])}}};"
    )
    lines.append("")

    for name, pid in pid_map.items():
        ident = to_identifier(name)
        values = [
            cpp_float(pid.get("kp", 0.0)),
            cpp_float(pid.get("ki", 0.0)),
            cpp_float(pid.get("kd", 0.0)),
            cpp_float(pid.get("output_limit", 0.0)),
            cpp_float(pid.get("integral_limit", 0.0)),
            cpp_float(pid.get("integral_separation_threshold", 0.0)),
            cpp_float(pid.get("R", 0.0)),
            cpp_float(pid.get("T", 0.0)),
        ]
        lines.append(
            f"    static constexpr ALG::PID::PidConfig kPid{ident} = "
            "{" + ", ".join(values) + "};"
        )
    lines.append("")

    lines.append("    struct PwmChannelConfig")
    lines.append("    {")
    lines.append("        const char *timer;")
    lines.append("        const char *channel;")
    lines.append("        const char *gpio;")
    lines.append("        bool complementary;")
    lines.append("    };")
    lines.append("")
    lines.append("    struct MotorConfig")
    lines.append("    {")
    lines.append("        const char *name;")
    lines.append("        const char *interface;")
    lines.append("        uint8_t ik_index;")
    lines.append("        const char *side;")
    lines.append("        const char *position;")
    lines.append("        PwmChannelConfig pwm_a;")
    lines.append("        PwmChannelConfig pwm_b;")
    lines.append("        const char *encoder;")
    lines.append("        const char *speed_pid;")
    lines.append("        bool reverse;")
    lines.append("        float reduction_ratio;")
    lines.append("    };")
    lines.append("")
    lines.append("    struct EncoderConfig")
    lines.append("    {")
    lines.append("        const char *name;")
    lines.append("        const char *interface;")
    lines.append("        const char *timer;")
    lines.append("        uint32_t cpr;")
    lines.append("    };")
    lines.append("")
    lines.append("    struct UartConfig")
    lines.append("    {")
    lines.append("        const char *name;")
    lines.append("        const char *logical_id;")
    lines.append("        const char *handle;")
    lines.append("        uint32_t baudrate;")
    lines.append("        const char *tx_mode;")
    lines.append("        const char *rx_mode;")
    lines.append("        uint16_t rx_buffer_size;")
    lines.append("        const char *rx_callback;")
    lines.append("    };")
    lines.append("")
    lines.append("    static constexpr MotorConfig kMotors[] =")
    lines.append("    {")
    for name, motor in sorted(motors.items(), key=lambda item: item[1]["ik_index"]):
        pwm_a = motor.get("pwm_a", {})
        pwm_b = motor.get("pwm_b", {})
        lines.append("        {")
        lines.append(f"            {cpp_string(name)},")
        lines.append(f"            {cpp_string(motor.get('interface', ''))},")
        lines.append(f"            {as_int(motor['ik_index'])},")
        lines.append(f"            {cpp_string(motor.get('side', ''))},")
        lines.append(f"            {cpp_string(motor.get('position', ''))},")
        lines.append(
            "            {"
            f"{cpp_string(pwm_a.get('timer', ''))}, "
            f"{cpp_string(pwm_a.get('channel', ''))}, "
            f"{cpp_string(pwm_a.get('gpio', ''))}, "
            f"{cpp_bool(pwm_a.get('complementary', False))}"
            "},"
        )
        lines.append(
            "            {"
            f"{cpp_string(pwm_b.get('timer', ''))}, "
            f"{cpp_string(pwm_b.get('channel', ''))}, "
            f"{cpp_string(pwm_b.get('gpio', ''))}, "
            f"{cpp_bool(pwm_b.get('complementary', False))}"
            "},"
        )
        lines.append(f"            {cpp_string(motor['encoder'])},")
        lines.append(f"            {cpp_string(motor['speed_pid'])},")
        lines.append(f"            {cpp_bool(motor.get('reverse', False))},")
        lines.append(f"            {cpp_float(motor['reduction_ratio'])}")
        lines.append("        },")
    lines.append("    };")
    lines.append("")

    lines.append("    static constexpr EncoderConfig kEncoders[] =")
    lines.append("    {")
    for name, encoder in encoders.items():
        lines.append(
            "        {"
            f"{cpp_string(name)}, "
            f"{cpp_string(encoder.get('interface', ''))}, "
            f"{cpp_string(encoder.get('timer', ''))}, "
            f"{as_int(encoder.get('cpr', 0))}u"
            "},"
        )
    lines.append("    };")
    lines.append("")

    lines.append("    static constexpr UartConfig kUarts[] =")
    lines.append("    {")
    for name, uart in uart_map.items():
        lines.append(
            "        {"
            f"{cpp_string(name)}, "
            f"{cpp_string(uart.get('logical_id', ''))}, "
            f"{cpp_string(uart.get('handle', ''))}, "
            f"{as_int(uart.get('baudrate', 0))}u, "
            f"{cpp_string(uart.get('tx_mode', ''))}, "
            f"{cpp_string(uart.get('rx_mode', ''))}, "
            f"{as_int(uart.get('rx_buffer_size', 0))}u, "
            f"{cpp_string(uart.get('rx_callback', ''))}"
            "},"
        )
    lines.append("    };")
    lines.append("")

    lines.append("    static constexpr uint8_t kMotorCount = sizeof(kMotors) / sizeof(kMotors[0]);")
    lines.append(
        "    static constexpr uint8_t kEncoderCount = sizeof(kEncoders) / sizeof(kEncoders[0]);"
    )
    lines.append("    static constexpr uint8_t kUartCount = sizeof(kUarts) / sizeof(kUarts[0]);")
    lines.append("}")
    lines.append("")
    lines.append("#endif // !ROBOT_CONFIG_HPP")
    lines.append("")
    return "\n".join(lines)


def generate_messages_header(config: dict, source_path: Path) -> str:
    messages = config.get("messages", {})

    lines = []
    lines.append("// Generated by src/Tools/script/yaml_to_config.py.")
    lines.append(f"// Source: {source_path.as_posix()}")
    lines.append("#ifndef ROBOT_MESSAGES_HPP")
    lines.append("#define ROBOT_MESSAGES_HPP")
    lines.append("")
    lines.append("#include <stdint.h>")
    lines.append("")
    lines.append('#include "message_bus.hpp"')
    lines.append("")
    lines.append("namespace RobotMessages")
    lines.append("{")

    for name, message in messages.items():
        ident = to_identifier(name)
        fields = message.get("fields", {})

        lines.append(f"    struct {ident}")
        lines.append("    {")
        for field_name, field_type in fields.items():
            lines.append(
                f"        {cpp_message_type(field_type)} {to_field_identifier(field_name)} = {{}};"
            )
        lines.append("    };")
        lines.append("")

        lines.append(
            f"    using {ident}Bus = MID::MessageBus::MessageBus<{ident}>;"
        )
        lines.append("")
        lines.append(f"    inline void Publish{ident}(const {ident} &msg)")
        lines.append("    {")
        lines.append(f"        {ident}Bus::Instance().Publish(msg);")
        lines.append("    }")
        lines.append("")
        lines.append(
            f"    inline bool Subscribe{ident}({ident}Bus::Subscriber subscriber)"
        )
        lines.append("    {")
        lines.append(f"        return {ident}Bus::Instance().Subscribe(subscriber);")
        lines.append("    }")
        lines.append("")

    lines.append("}")
    lines.append("")
    lines.append("#endif // !ROBOT_MESSAGES_HPP")
    lines.append("")
    return "\n".join(lines)


def generate_runtime_header(config: dict, source_path: Path) -> str:
    pid_map = config["control"]["pid"]
    motors = config["hardware"]["motors"]
    encoders = config["hardware"]["encoders"]
    motors_by_index = sorted(motors.items(), key=lambda item: item[1]["ik_index"])
    motor_for_encoder = {
        motor["encoder"]: (name, motor)
        for name, motor in motors.items()
    }

    lines = []
    lines.append("// Generated by src/Tools/script/yaml_to_config.py.")
    lines.append(f"// Source: {source_path.as_posix()}")
    lines.append("#ifndef ROBOT_RUNTIME_HPP")
    lines.append("#define ROBOT_RUNTIME_HPP")
    lines.append("")
    lines.append('#include "pid.hpp"')
    lines.append('#include "tim.h"')
    lines.append('#include "drv_pwm.hpp"')
    lines.append('#include "encoder.hpp"')
    lines.append('#include "310Motor.hpp"')
    lines.append('#include "robot_config.hpp"')
    lines.append("")
    lines.append("namespace RobotRuntime")
    lines.append("{")

    for name in pid_map.keys():
        ident = to_identifier(name)
        lines.append(f"    inline ALG::PID::PID &{ident}Pid()")
        lines.append("    {")
        lines.append(
            f"        static ALG::PID::PID pid(RobotConfig::kPid{ident});"
        )
        lines.append("        return pid;")
        lines.append("    }")
        lines.append("")

    for name, encoder in encoders.items():
        ident = to_identifier(name)
        if name not in motor_for_encoder:
            raise ConfigError(f"Encoder {name} is not referenced by any motor")
        _, motor = motor_for_encoder[name]
        pid_ident = to_identifier(motor["speed_pid"])

        lines.append(f"    inline BSP::ENCODER::HALEncoder &{ident}Hal()")
        lines.append("    {")
        lines.append(
            f"        static BSP::ENCODER::HALEncoder encoder(&{cpp_symbol(encoder['timer'])});"
        )
        lines.append("        return encoder;")
        lines.append("    }")
        lines.append("")
        lines.append(f"    inline BSP::ENCODER::EncoderData &{ident}Data()")
        lines.append("    {")
        lines.append(
            f"        static BSP::ENCODER::EncoderData data({ident}Hal(), "
            f"RobotConfig::kEncoders[{list(encoders.keys()).index(name)}].cpr, "
            f"RobotConfig::kPid{pid_ident}.T);"
        )
        lines.append("        return data;")
        lines.append("    }")
        lines.append("")

    for index, (name, motor) in enumerate(motors_by_index):
        ident = to_identifier(name)
        pwm_a = motor["pwm_a"]
        pwm_b = motor["pwm_b"]

        lines.append(f"    inline DRV::PWM::HalPwmChannel &{ident}PwmA()")
        lines.append("    {")
        lines.append(
            f"        static DRV::PWM::HalPwmChannel pwm(&{cpp_symbol(pwm_a['timer'])}, "
            f"{cpp_symbol(pwm_a['channel'])});"
        )
        lines.append("        return pwm;")
        lines.append("    }")
        lines.append("")
        lines.append(f"    inline DRV::PWM::HalPwmChannel &{ident}PwmB()")
        lines.append("    {")
        lines.append(
            f"        static DRV::PWM::HalPwmChannel pwm(&{cpp_symbol(pwm_b['timer'])}, "
            f"{cpp_symbol(pwm_b['channel'])});"
        )
        lines.append("        return pwm;")
        lines.append("    }")
        lines.append("")

    motor_id_names = [
        "LeftForward",
        "RightForward",
        "LeftBackward",
        "RightBackward",
    ]
    lines.append("    inline BSP::Motor::_310::MotorConfig (&ChassisMotorConfigs())[4]")
    lines.append("    {")
    lines.append("        static BSP::Motor::_310::MotorConfig configs[4] =")
    lines.append("        {")
    for index, (name, motor) in enumerate(motors_by_index):
        ident = to_identifier(name)
        encoder_ident = to_identifier(motor["encoder"])
        lines.append(
            "            {"
            f"BSP::Motor::_310::MotorId::{motor_id_names[index]}, "
            f"&{ident}PwmA(), "
            f"&{ident}PwmB(), "
            f"&{encoder_ident}Data(), "
            f"BSP::Motor::_310::Parameters(RobotConfig::kMotors[{index}].reduction_ratio)"
            "},"
        )
    lines.append("        };")
    lines.append("")
    lines.append("        return configs;")
    lines.append("    }")
    lines.append("")
    lines.append("    inline BSP::Motor::_310::Motor310<4> &ChassisMotors()")
    lines.append("    {")
    lines.append("        static BSP::Motor::_310::Motor310<4> motors(ChassisMotorConfigs());")
    lines.append("        return motors;")
    lines.append("    }")
    lines.append("")

    lines.append("}")
    lines.append("")
    lines.append("#endif // !ROBOT_RUNTIME_HPP")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate C++ config from YAML.")
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--messages-output", type=Path, default=DEFAULT_MESSAGES_OUTPUT)
    parser.add_argument("--runtime-output", type=Path, default=DEFAULT_RUNTIME_OUTPUT)
    args = parser.parse_args()

    config = load_yaml_subset(args.input)
    validate_config(config)
    header = generate_header(config, args.input)
    messages_header = generate_messages_header(config, args.input)
    runtime_header = generate_runtime_header(config, args.input)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(header, encoding="utf-8", newline="\n")
    args.messages_output.parent.mkdir(parents=True, exist_ok=True)
    args.messages_output.write_text(messages_header, encoding="utf-8", newline="\n")
    args.runtime_output.parent.mkdir(parents=True, exist_ok=True)
    args.runtime_output.write_text(runtime_header, encoding="utf-8", newline="\n")
    print(f"generated: {args.output}")
    print(f"generated: {args.messages_output}")
    print(f"generated: {args.runtime_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
