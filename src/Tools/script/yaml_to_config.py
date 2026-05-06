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
    return f"{as_float(value):.9g}f"


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

    if seen_indexes != {0, 1, 2, 3}:
        raise ConfigError("Motors must define ik_index 0, 1, 2, and 3")

    for name, pid in pid_map.items():
        for field in ("kp", "ki", "kd", "output_limit", "integral_limit", "T"):
            require(pid, field, f"control.pid.{name}")


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
    lines.append("    };")
    lines.append("")
    lines.append("    struct EncoderConfig")
    lines.append("    {")
    lines.append("        const char *name;")
    lines.append("        const char *interface;")
    lines.append("        const char *timer;")
    lines.append("        const char *channel_a_gpio;")
    lines.append("        const char *channel_a;")
    lines.append("        const char *channel_b_gpio;")
    lines.append("        const char *channel_b;")
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
    lines.append("    struct MessageConfig")
    lines.append("    {")
    lines.append("        const char *name;")
    lines.append("        const char *publisher;")
    lines.append("        const char *subscribers[4];")
    lines.append("        uint8_t subscriber_count;")
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
        lines.append(f"            {cpp_bool(motor.get('reverse', False))}")
        lines.append("        },")
    lines.append("    };")
    lines.append("")

    lines.append("    static constexpr EncoderConfig kEncoders[] =")
    lines.append("    {")
    for name, encoder in encoders.items():
        channel_a = encoder.get("channel_a", {})
        channel_b = encoder.get("channel_b", {})
        lines.append(
            "        {"
            f"{cpp_string(name)}, "
            f"{cpp_string(encoder.get('interface', ''))}, "
            f"{cpp_string(encoder.get('timer', ''))}, "
            f"{cpp_string(channel_a.get('gpio', ''))}, "
            f"{cpp_string(channel_a.get('channel', ''))}, "
            f"{cpp_string(channel_b.get('gpio', ''))}, "
            f"{cpp_string(channel_b.get('channel', ''))}"
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

    lines.append("    static constexpr MessageConfig kMessages[] =")
    lines.append("    {")
    for name, message in messages.items():
        subscribers = list(message.get("subscribers", []))
        if len(subscribers) > 4:
            raise ConfigError(f"Message {name} has more than 4 subscribers")
        padded = subscribers + [""] * (4 - len(subscribers))
        lines.append(
            "        {"
            f"{cpp_string(name)}, "
            f"{cpp_string(message.get('publisher', ''))}, "
            "{"
            + ", ".join(cpp_string(item) for item in padded)
            + "}, "
            f"{len(subscribers)}u"
            "},"
        )
    lines.append("    };")
    lines.append("")

    lines.append("    static constexpr uint8_t kMotorCount = sizeof(kMotors) / sizeof(kMotors[0]);")
    lines.append(
        "    static constexpr uint8_t kEncoderCount = sizeof(kEncoders) / sizeof(kEncoders[0]);"
    )
    lines.append("    static constexpr uint8_t kUartCount = sizeof(kUarts) / sizeof(kUarts[0]);")
    lines.append(
        "    static constexpr uint8_t kMessageCount = sizeof(kMessages) / sizeof(kMessages[0]);"
    )
    lines.append("}")
    lines.append("")
    lines.append("#endif // !ROBOT_CONFIG_HPP")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate C++ config from YAML.")
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    config = load_yaml_subset(args.input)
    validate_config(config)
    header = generate_header(config, args.input)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(header, encoding="utf-8", newline="\n")
    print(f"generated: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
