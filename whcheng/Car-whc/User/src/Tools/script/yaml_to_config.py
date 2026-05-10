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
DEFAULT_UART_OUTPUT = ROOT / "src" / "Tools" / "generated" / "robot_uart.hpp"
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


def as_uint(value, path: str) -> int:
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and re.fullmatch(r"0[xX][0-9A-Fa-f]+", value):
        result = int(value, 16)
    else:
        raise ConfigError(f"{path} must be an integer or hex string")
    if result < 0:
        raise ConfigError(f"{path} must be non-negative")
    return result


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


def as_bool(value) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"Expected bool, got {value!r}")
    return value


def grouped_array_enabled(flags: list[bool], path: str) -> bool:
    if any(flags) and not all(flags):
        raise ConfigError(f"{path}.array must be true for every item in the group or omitted for every item")
    return all(flags)


def collect_array_groups(items: dict, path: str) -> dict:
    groups: dict[str, list[tuple[int, str]]] = {}
    for name, item in items.items():
        if not bool(item.get("array", False)):
            continue

        array_name = require(item, "array_name", f"{path}.{name}")
        if not isinstance(array_name, str):
            raise ConfigError(f"{path}.{name}.array_name must be a string")
        to_identifier(array_name)

        array_index = as_int(require(item, "array_index", f"{path}.{name}"))
        if array_index < 0:
            raise ConfigError(f"{path}.{name}.array_index must be non-negative")

        groups.setdefault(array_name, []).append((array_index, name))

    for array_name, items in groups.items():
        indexes = [index for index, _ in items]
        if len(indexes) != len(set(indexes)):
            raise ConfigError(f"{path} array group {array_name} has duplicated array_index")
        expected = set(range(len(indexes)))
        if set(indexes) != expected:
            raise ConfigError(
                f"{path} array group {array_name} must use continuous array_index 0..{len(indexes) - 1}"
            )

    return groups


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


def validate_message_fields(fields: dict, path: str) -> None:
    for field_name, field_value in fields.items():
        to_field_identifier(field_name)
        if isinstance(field_value, dict):
            count = as_int(require(field_value, "count", f"{path}.{field_name}"))
            if count <= 0:
                raise ConfigError(f"{path}.{field_name}.count must be positive")
            nested = require(field_value, "fields", f"{path}.{field_name}")
            if not isinstance(nested, dict) or not nested:
                raise ConfigError(f"{path}.{field_name}.fields must be a non-empty map")
            validate_message_fields(nested, f"{path}.{field_name}.fields")
        else:
            cpp_message_type(field_value)


def generate_message_field_lines(lines: list[str], fields: dict, indent: str) -> None:
    for field_name, field_value in fields.items():
        field_ident = to_field_identifier(field_name)
        if isinstance(field_value, dict):
            item_ident = f"{to_identifier(field_name)}Item"
            count = as_int(field_value["count"])
            lines.append(f"{indent}struct {item_ident}")
            lines.append(f"{indent}{{")
            generate_message_field_lines(lines, field_value["fields"], indent + "    ")
            lines.append(f"{indent}}};")
            lines.append(f"{indent}{item_ident} {field_ident}[{count}] = {{}};")
        else:
            lines.append(f"{indent}{cpp_message_type(field_value)} {field_ident} = {{}};")


def cpp_symbol(value) -> str:
    text = str(value)
    if not re.fullmatch(r"[A-Za-z_][0-9A-Za-z_]*", text):
        raise ConfigError(f"Expected C++ symbol, got {text!r}")
    return text


def parse_gpio_pin(pin: str, path: str) -> tuple[str, str]:
    if not isinstance(pin, str):
        raise ConfigError(f"{path}.pin must be a string")

    match = re.fullmatch(r"P([A-G])(\d{1,2})", pin)
    if not match:
        raise ConfigError(f"{path}.pin must look like PA0..PG15, got {pin!r}")

    port = f"GPIO{match.group(1)}"
    pin_index = as_int(int(match.group(2)))
    if pin_index < 0 or pin_index > 15:
        raise ConfigError(f"{path}.pin must be in range P[A-G]0..15")

    return port, f"GPIO_PIN_{pin_index}"


def cpp_gpio_pin_expr(pin: str, path: str) -> str:
    port, pin_expr = parse_gpio_pin(pin, path)
    return f"{port}, {pin_expr}"


def wheel_order_key(name: str) -> int:
    text = name.lower()
    if "left_front" in text:
        return 0
    if "right_front" in text:
        return 1
    if "left_back" in text:
        return 2
    if "right_back" in text:
        return 3
    return 99


def validate_gpio_common(mapping: dict, path: str, extra_fields: tuple[str, ...]) -> None:
    require(mapping, "pin", path)
    pin = mapping["pin"]
    if not isinstance(pin, str):
        raise ConfigError(f"{path}.pin must be a string")
    parse_gpio_pin(pin, path)

    active_low = mapping.get("active_low", None)
    if active_low is not None:
        as_bool(active_low)

    for field in extra_fields:
        if field in mapping and not isinstance(mapping[field], str):
            raise ConfigError(f"{path}.{field} must be a string")


def get_optional_map(mapping: dict, key: str, path: str) -> dict:
    value = mapping.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"{path}.{key} must be a map")
    return value


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
    filters = get_optional_map(control, "filters", "control")
    feedforwards = get_optional_map(control, "feedforwards", "control")
    observers = get_optional_map(control, "observers", "control")
    hardware = require(config, "hardware", "config")
    motors = require(hardware, "motors", "hardware")
    encoders = require(hardware, "encoders", "hardware")
    buttons = get_optional_map(hardware, "buttons", "hardware")
    leds = get_optional_map(hardware, "leds", "hardware")
    buzzer = get_optional_map(hardware, "buzzer", "hardware")
    oled = get_optional_map(hardware, "oled", "hardware")
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
        if "array" in motor:
            as_bool(motor["array"])
            require(motor, "array_name", f"hardware.motors.{name}")
            require(motor, "array_index", f"hardware.motors.{name}")

    if seen_indexes != {0, 1, 2, 3}:
        raise ConfigError("Motors must define ik_index 0, 1, 2, and 3")

    for name, pid in pid_map.items():
        for field in ("kp", "ki", "kd", "output_limit", "integral_limit", "T"):
            require(pid, field, f"control.pid.{name}")
        if "array" in pid:
            as_bool(pid["array"])
            require(pid, "array_name", f"control.pid.{name}")
            require(pid, "array_index", f"control.pid.{name}")

    for name, filter_config in filters.items():
        filter_type = require(filter_config, "type", f"control.filters.{name}")
        if "array" in filter_config:
            as_bool(filter_config["array"])
            require(filter_config, "array_name", f"control.filters.{name}")
            require(filter_config, "array_index", f"control.filters.{name}")
        if filter_type == "low_pass":
            alpha = as_float(require(filter_config, "alpha", f"control.filters.{name}"))
            if alpha < 0.0 or alpha > 1.0:
                raise ConfigError(f"control.filters.{name}.alpha must be between 0 and 1")
            as_float(filter_config.get("initial_output", 0.0))
        elif filter_type == "td":
            r = as_float(require(filter_config, "r", f"control.filters.{name}"))
            h = as_float(require(filter_config, "h", f"control.filters.{name}"))
            if r <= 0.0:
                raise ConfigError(f"control.filters.{name}.r must be positive")
            if h <= 0.0:
                raise ConfigError(f"control.filters.{name}.h must be positive")
            as_float(filter_config.get("initial_v1", 0.0))
            as_float(filter_config.get("initial_v2", 0.0))
        else:
            raise ConfigError(f"control.filters.{name}.type must be low_pass or td")

    filter_array_groups = collect_array_groups(filters, "control.filters")
    for array_name, items in filter_array_groups.items():
        filter_types = {filters[name]["type"] for _, name in items}
        if len(filter_types) != 1:
            raise ConfigError(f"control.filters array group {array_name} must use one filter type")

    for name, feedforward in feedforwards.items():
        ff_type = require(feedforward, "type", f"control.feedforwards.{name}")
        if "array" in feedforward:
            as_bool(feedforward["array"])
            require(feedforward, "array_name", f"control.feedforwards.{name}")
            require(feedforward, "array_index", f"control.feedforwards.{name}")
        if ff_type == "acceleration":
            as_float(require(feedforward, "k_acc", f"control.feedforwards.{name}"))
            cycle = as_float(require(feedforward, "control_cycle", f"control.feedforwards.{name}"))
            if cycle <= 0.0:
                raise ConfigError(f"control.feedforwards.{name}.control_cycle must be positive")
            as_float(feedforward.get("initial_target", 0.0))
        elif ff_type == "velocity":
            as_float(require(feedforward, "k_vel", f"control.feedforwards.{name}"))
            cycle = as_float(require(feedforward, "control_cycle", f"control.feedforwards.{name}"))
            if cycle <= 0.0:
                raise ConfigError(f"control.feedforwards.{name}.control_cycle must be positive")
            as_float(feedforward.get("initial_target", 0.0))
        elif ff_type == "gravity":
            as_float(require(feedforward, "k_gravity", f"control.feedforwards.{name}"))
            as_float(require(feedforward, "phi_deg", f"control.feedforwards.{name}"))
        elif ff_type == "friction":
            as_float(require(feedforward, "friction_value", f"control.feedforwards.{name}"))
        elif ff_type == "gimbal_full_compensation":
            as_float(require(feedforward, "k_j", f"control.feedforwards.{name}"))
            dt = as_float(require(feedforward, "control_dt", f"control.feedforwards.{name}"))
            if dt <= 0.0:
                raise ConfigError(f"control.feedforwards.{name}.control_dt must be positive")
            as_float(require(feedforward, "viscous_friction", f"control.feedforwards.{name}"))
            as_float(require(feedforward, "coulomb_friction", f"control.feedforwards.{name}"))
            deadzone = as_float(feedforward.get("deadzone", 3.0))
            alpha = as_float(feedforward.get("acc_filter_alpha", 0.15))
            if deadzone < 0.0:
                raise ConfigError(f"control.feedforwards.{name}.deadzone must be non-negative")
            if alpha < 0.0 or alpha > 1.0:
                raise ConfigError(f"control.feedforwards.{name}.acc_filter_alpha must be between 0 and 1")
        else:
            raise ConfigError(
                f"control.feedforwards.{name}.type must be acceleration, velocity, gravity, friction, or gimbal_full_compensation"
            )

    feedforward_array_groups = collect_array_groups(feedforwards, "control.feedforwards")
    for array_name, items in feedforward_array_groups.items():
        ff_types = {feedforwards[name]["type"] for _, name in items}
        if len(ff_types) != 1:
            raise ConfigError(f"control.feedforwards array group {array_name} must use one feedforward type")

    for name, observer in observers.items():
        observer_type = require(observer, "type", f"control.observers.{name}")
        if "array" in observer:
            as_bool(observer["array"])
            require(observer, "array_name", f"control.observers.{name}")
            require(observer, "array_index", f"control.observers.{name}")
        if observer_type == "ude":
            as_float(require(observer, "a", f"control.observers.{name}"))
            b = as_float(require(observer, "b", f"control.observers.{name}"))
            if b == 0.0:
                raise ConfigError(f"control.observers.{name}.b must not be zero")
            as_float(observer.get("initial_feedback", 0.0))
        else:
            raise ConfigError(f"control.observers.{name}.type must be ude")

    collect_array_groups(observers, "control.observers")

    for name, encoder in encoders.items():
        cpr = as_int(require(encoder, "cpr", f"hardware.encoders.{name}"))
        if cpr <= 0:
            raise ConfigError(f"hardware.encoders.{name}.cpr must be positive")
        if "array" in encoder:
            as_bool(encoder["array"])
            require(encoder, "array_name", f"hardware.encoders.{name}")
            require(encoder, "array_index", f"hardware.encoders.{name}")

    for name, button in buttons.items():
        validate_gpio_common(button, f"hardware.buttons.{name}", ("mode", "trigger", "pull", "irq"))
        if "mode" in button and button["mode"] not in {"exti", "input"}:
            raise ConfigError(f"hardware.buttons.{name}.mode must be exti or input")
        if "trigger" in button and button["trigger"] not in {"rising", "falling", "both"}:
            raise ConfigError(f"hardware.buttons.{name}.trigger must be rising, falling, or both")
        if "pull" in button and button["pull"] not in {"none", "up", "down"}:
            raise ConfigError(f"hardware.buttons.{name}.pull must be none, up, or down")

    for name, led in leds.items():
        validate_gpio_common(led, f"hardware.leds.{name}", ("mode", "pull", "speed"))
        if "mode" in led and led["mode"] not in {"output"}:
            raise ConfigError(f"hardware.leds.{name}.mode must be output")
        if "pull" in led and led["pull"] not in {"none", "up", "down"}:
            raise ConfigError(f"hardware.leds.{name}.pull must be none, up, or down")
        if "speed" in led and led["speed"] not in {"low", "medium", "high", "very_high"}:
            raise ConfigError(
                f"hardware.leds.{name}.speed must be low, medium, high, or very_high"
            )

    if buzzer:
        validate_gpio_common(buzzer, "hardware.buzzer", ("mode", "pull", "speed"))
        if "mode" in buzzer and buzzer["mode"] not in {"output"}:
            raise ConfigError("hardware.buzzer.mode must be output")
        if "pull" in buzzer and buzzer["pull"] not in {"none", "up", "down"}:
            raise ConfigError("hardware.buzzer.pull must be none, up, or down")
        if "speed" in buzzer and buzzer["speed"] not in {"low", "medium", "high", "very_high"}:
            raise ConfigError("hardware.buzzer.speed must be low, medium, high, or very_high")

    if oled:
        oled_type = require(oled, "type", "hardware.oled")
        if oled_type not in {"ssd1306_i2c"}:
            raise ConfigError("hardware.oled.type must be ssd1306_i2c")
        i2c_handle = require(oled, "i2c_handle", "hardware.oled")
        if not isinstance(i2c_handle, str):
            raise ConfigError("hardware.oled.i2c_handle must be a string")
        cpp_symbol(i2c_handle)
        address = as_uint(require(oled, "address", "hardware.oled"), "hardware.oled.address")
        if address > 0x7F:
            raise ConfigError("hardware.oled.address must be a 7-bit I2C address")
        width = as_int(require(oled, "width", "hardware.oled"))
        height = as_int(require(oled, "height", "hardware.oled"))
        if width != 128:
            raise ConfigError("hardware.oled.width must be 128")
        if height != 64:
            raise ConfigError("hardware.oled.height must be 64")

    uart_map = config.get("communication", {}).get("uart", {})
    if not isinstance(uart_map, dict):
        raise ConfigError("communication.uart must be a map")

    uart_logical_ids = set()
    uart_handles = set()
    for name, uart in uart_map.items():
        logical_id = require(uart, "logical_id", f"communication.uart.{name}")
        if not isinstance(logical_id, str):
            raise ConfigError(f"communication.uart.{name}.logical_id must be a string")
        to_identifier(logical_id)
        if logical_id in uart_logical_ids:
            raise ConfigError(f"Duplicated communication.uart logical_id: {logical_id}")
        uart_logical_ids.add(logical_id)

        handle = require(uart, "handle", f"communication.uart.{name}")
        if not isinstance(handle, str):
            raise ConfigError(f"communication.uart.{name}.handle must be a string")
        cpp_symbol(handle)
        if handle in uart_handles:
            raise ConfigError(f"Duplicated communication.uart handle: {handle}")
        uart_handles.add(handle)

        baudrate = as_int(require(uart, "baudrate", f"communication.uart.{name}"))
        if baudrate <= 0:
            raise ConfigError(f"communication.uart.{name}.baudrate must be positive")

        tx_mode = require(uart, "tx_mode", f"communication.uart.{name}")
        if tx_mode not in {"dma", "it", "blocking"}:
            raise ConfigError(f"Unsupported communication.uart.{name}.tx_mode: {tx_mode}")

        rx_mode = require(uart, "rx_mode", f"communication.uart.{name}")
        if rx_mode not in {"idle_dma", "dma", "it", "blocking"}:
            raise ConfigError(f"Unsupported communication.uart.{name}.rx_mode: {rx_mode}")

        rx_buffer_size = as_int(require(uart, "rx_buffer_size", f"communication.uart.{name}"))
        if rx_buffer_size <= 0:
            raise ConfigError(f"communication.uart.{name}.rx_buffer_size must be positive")

        rx_callback = uart.get("rx_callback", "")
        if rx_callback != "":
            if not isinstance(rx_callback, str):
                raise ConfigError(f"communication.uart.{name}.rx_callback must be a string")
            cpp_symbol(rx_callback)

    collect_array_groups(pid_map, "control.pid")
    collect_array_groups(motors, "hardware.motors")
    collect_array_groups(encoders, "hardware.encoders")

    for name, message in messages.items():
        fields = require(message, "fields", f"messages.{name}")
        if not isinstance(fields, dict) or not fields:
            raise ConfigError(f"messages.{name}.fields must be a non-empty map")
        validate_message_fields(fields, f"messages.{name}.fields")

        subscribers = message.get("subscribers", [])
        if not isinstance(subscribers, list):
            raise ConfigError(f"messages.{name}.subscribers must be a list")
        if len(subscribers) > 4:
            raise ConfigError(f"Message {name} has more than 4 subscribers")


def generate_uart_header(config: dict, source_path: Path) -> str:
    uart_map = config.get("communication", {}).get("uart", {})

    lines = []
    lines.append("// Generated by src/Tools/script/yaml_to_config.py.")
    lines.append(f"// Source: {source_path.as_posix()}")
    lines.append("#ifndef ROBOT_UART_HPP")
    lines.append("#define ROBOT_UART_HPP")
    lines.append("")
    lines.append("#include <stdint.h>")
    lines.append("")
    lines.append("namespace DRV::UART")
    lines.append("{")
    lines.append("    enum class UartId : uint8_t")
    lines.append("    {")

    items = list(uart_map.items())
    if items:
        for index, (_, uart) in enumerate(items):
            uart_ident = to_identifier(uart["logical_id"])
            lines.append(f"        {uart_ident} = {index},")
        lines.append("        Count")
    else:
        lines.append("        Count = 0")

    lines.append("    };")
    lines.append("}")
    lines.append("")
    lines.append("#endif // !ROBOT_UART_HPP")
    lines.append("")
    return "\n".join(lines)


def generate_header(config: dict, source_path: Path) -> str:
    robot = config["robot"]
    control = config["control"]
    ik_config = control["chassis_ik"]["config"]
    pid_map = control["pid"]
    filters = get_optional_map(control, "filters", "control")
    feedforwards = get_optional_map(control, "feedforwards", "control")
    observers = get_optional_map(control, "observers", "control")
    hardware = config["hardware"]
    motors = hardware["motors"]
    encoders = hardware["encoders"]
    buttons = get_optional_map(hardware, "buttons", "hardware")
    leds = get_optional_map(hardware, "leds", "hardware")
    buzzer = get_optional_map(hardware, "buzzer", "hardware")
    oled = get_optional_map(hardware, "oled", "hardware")
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
    lines.append('#include "filter.hpp"')
    lines.append('#include "feedforward.hpp"')
    lines.append('#include "observer.hpp"')
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

    for name, filter_config in filters.items():
        ident = to_identifier(name)
        filter_type = filter_config["type"]
        if filter_type == "low_pass":
            lines.append(
                f"    static constexpr ALG::Filter::LowPassFilterConfig kFilter{ident} = "
                "{"
                f"{cpp_float(filter_config['alpha'])}, "
                f"{cpp_float(filter_config.get('initial_output', 0.0))}"
                "};"
            )
        elif filter_type == "td":
            lines.append(
                f"    static constexpr ALG::Filter::TDFilterConfig kFilter{ident} = "
                "{"
                f"{cpp_float(filter_config['r'])}, "
                f"{cpp_float(filter_config['h'])}, "
                f"{cpp_float(filter_config.get('initial_v1', 0.0))}, "
                f"{cpp_float(filter_config.get('initial_v2', 0.0))}"
                "};"
            )
    if filters:
        lines.append("")

    for name, feedforward in feedforwards.items():
        ident = to_identifier(name)
        ff_type = feedforward["type"]
        if ff_type == "acceleration":
            lines.append(
                f"    static constexpr ALG::Feedforward::AccelerationFeedforwardConfig kFeedforward{ident} = "
                "{"
                f"{cpp_float(feedforward['k_acc'])}, "
                f"{cpp_float(feedforward['control_cycle'])}, "
                f"{cpp_float(feedforward.get('initial_target', 0.0))}"
                "};"
            )
        elif ff_type == "velocity":
            lines.append(
                f"    static constexpr ALG::Feedforward::VelocityFeedforwardConfig kFeedforward{ident} = "
                "{"
                f"{cpp_float(feedforward['k_vel'])}, "
                f"{cpp_float(feedforward['control_cycle'])}, "
                f"{cpp_float(feedforward.get('initial_target', 0.0))}"
                "};"
            )
        elif ff_type == "gravity":
            lines.append(
                f"    static constexpr ALG::Feedforward::GravityFeedforwardConfig kFeedforward{ident} = "
                "{"
                f"{cpp_float(feedforward['k_gravity'])}, "
                f"{cpp_float(feedforward['phi_deg'])}"
                "};"
            )
        elif ff_type == "friction":
            lines.append(
                f"    static constexpr ALG::Feedforward::FrictionFeedforwardConfig kFeedforward{ident} = "
                "{"
                f"{cpp_float(feedforward['friction_value'])}"
                "};"
            )
        elif ff_type == "gimbal_full_compensation":
            lines.append(
                f"    static constexpr ALG::Feedforward::GimbalFullCompensationConfig kFeedforward{ident} = "
                "{"
                f"{cpp_float(feedforward['k_j'])}, "
                f"{cpp_float(feedforward['control_dt'])}, "
                f"{cpp_float(feedforward['viscous_friction'])}, "
                f"{cpp_float(feedforward['coulomb_friction'])}, "
                f"{cpp_float(feedforward.get('deadzone', 3.0))}, "
                f"{cpp_float(feedforward.get('acc_filter_alpha', 0.15))}"
                "};"
            )
    if feedforwards:
        lines.append("")

    for name, observer in observers.items():
        ident = to_identifier(name)
        if observer["type"] == "ude":
            lines.append(
                f"    static constexpr ALG::Observer::UDEConfig kObserver{ident} = "
                "{"
                f"{cpp_float(observer['a'])}, "
                f"{cpp_float(observer['b'])}, "
                f"{cpp_float(observer.get('initial_feedback', 0.0))}"
                "};"
            )
    if observers:
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

    lines.append("    struct ButtonConfig")
    lines.append("    {")
    lines.append("        const char *name;")
    lines.append("        const char *pin;")
    lines.append("        const char *mode;")
    lines.append("        const char *trigger;")
    lines.append("        const char *pull;")
    lines.append("        const char *irq;")
    lines.append("        bool active_low;")
    lines.append("    };")
    lines.append("")

    lines.append("    struct LedConfig")
    lines.append("    {")
    lines.append("        const char *name;")
    lines.append("        const char *pin;")
    lines.append("        const char *mode;")
    lines.append("        const char *pull;")
    lines.append("        const char *speed;")
    lines.append("        bool active_low;")
    lines.append("    };")
    lines.append("")

    lines.append("    struct BuzzerConfig")
    lines.append("    {")
    lines.append("        const char *pin;")
    lines.append("        const char *mode;")
    lines.append("        const char *pull;")
    lines.append("        const char *speed;")
    lines.append("        bool active_low;")
    lines.append("    };")
    lines.append("")

    lines.append("    struct OledConfig")
    lines.append("    {")
    lines.append("        const char *type;")
    lines.append("        const char *i2c_handle;")
    lines.append("        uint8_t address;")
    lines.append("        uint8_t width;")
    lines.append("        uint8_t height;")
    lines.append("    };")
    lines.append("")
    lines.append("    static constexpr MotorConfig kMotors[] =")
    lines.append("    {")
    for name, motor in sorted(motors.items(), key=lambda item: wheel_order_key(item[0])):
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
    for name, encoder in sorted(encoders.items(), key=lambda item: wheel_order_key(item[0])):
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

    if buttons:
        lines.append("    static constexpr ButtonConfig kButtons[] =")
        lines.append("    {")
        for name, button in buttons.items():
            lines.append(
                "        {"
                f"{cpp_string(name)}, "
                f"{cpp_string(button.get('pin', ''))}, "
                f"{cpp_string(button.get('mode', 'exti'))}, "
                f"{cpp_string(button.get('trigger', 'rising'))}, "
                f"{cpp_string(button.get('pull', 'none'))}, "
                f"{cpp_string(button.get('irq', ''))}, "
                f"{cpp_bool(button.get('active_low', True))}"
                "},"
            )
        lines.append("    };")
        lines.append("")
    else:
        lines.append("    static constexpr uint8_t kButtonCount = 0;")
        lines.append("")

    if leds:
        lines.append("    static constexpr LedConfig kLeds[] =")
        lines.append("    {")
        for name, led in leds.items():
            lines.append(
                "        {"
                f"{cpp_string(name)}, "
                f"{cpp_string(led.get('pin', ''))}, "
                f"{cpp_string(led.get('mode', 'output'))}, "
                f"{cpp_string(led.get('pull', 'none'))}, "
                f"{cpp_string(led.get('speed', 'low'))}, "
                f"{cpp_bool(led.get('active_low', False))}"
                "},"
            )
        lines.append("    };")
        lines.append("")
    else:
        lines.append("    static constexpr uint8_t kLedCount = 0;")
        lines.append("")

    if buzzer:
        lines.append("    static constexpr BuzzerConfig kBuzzer =")
        lines.append("    {")
        lines.append(
            "        "
            f"{cpp_string(buzzer.get('pin', ''))}, "
            f"{cpp_string(buzzer.get('mode', 'output'))}, "
            f"{cpp_string(buzzer.get('pull', 'none'))}, "
            f"{cpp_string(buzzer.get('speed', 'low'))}, "
            f"{cpp_bool(buzzer.get('active_low', False))}"
        )
        lines.append("    };")
        lines.append("")

    if oled:
        lines.append("    static constexpr OledConfig kOled =")
        lines.append("    {")
        lines.append(
            "        "
            f"{cpp_string(oled.get('type', ''))}, "
            f"{cpp_string(oled.get('i2c_handle', ''))}, "
            f"0x{as_uint(oled.get('address', 0), 'hardware.oled.address'):02X}u, "
            f"{as_int(oled.get('width', 0))}u, "
            f"{as_int(oled.get('height', 0))}u"
        )
        lines.append("    };")
        lines.append("")

    lines.append("    static constexpr uint8_t kMotorCount = sizeof(kMotors) / sizeof(kMotors[0]);")
    lines.append(
        "    static constexpr uint8_t kEncoderCount = sizeof(kEncoders) / sizeof(kEncoders[0]);"
    )
    lines.append("    static constexpr uint8_t kUartCount = sizeof(kUarts) / sizeof(kUarts[0]);")
    if buttons:
        lines.append("    static constexpr uint8_t kButtonCount = sizeof(kButtons) / sizeof(kButtons[0]);")
    if leds:
        lines.append("    static constexpr uint8_t kLedCount = sizeof(kLeds) / sizeof(kLeds[0]);")
    lines.append(
        f"    static constexpr bool kHasBuzzer = {cpp_bool(bool(buzzer))};"
    )
    lines.append(
        f"    static constexpr bool kHasOled = {cpp_bool(bool(oled))};"
    )
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
        generate_message_field_lines(lines, fields, "        ")
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
    filters = get_optional_map(config["control"], "filters", "control")
    chassis_ik = config["control"]["chassis_ik"]
    motors = config["hardware"]["motors"]
    encoders = config["hardware"]["encoders"]
    hardware = config["hardware"]
    buttons = get_optional_map(hardware, "buttons", "hardware")
    leds = get_optional_map(hardware, "leds", "hardware")
    buzzer = get_optional_map(hardware, "buzzer", "hardware")
    oled = get_optional_map(hardware, "oled", "hardware")
    uart_map = config.get("communication", {}).get("uart", {})
    motors_by_index = sorted(motors.items(), key=lambda item: wheel_order_key(item[0]))
    pid_array_groups = collect_array_groups(pid_map, "control.pid")
    filter_array_groups = collect_array_groups(filters, "control.filters")
    motor_array_groups = collect_array_groups(motors, "hardware.motors")
    encoder_array_groups = collect_array_groups(encoders, "hardware.encoders")
    pid_names_in_arrays = {
        name
        for items in pid_array_groups.values()
        for _, name in items
    }
    filter_names_in_arrays = {
        name
        for items in filter_array_groups.values()
        for _, name in items
    }
    if len(motor_array_groups) > 1:
        raise ConfigError("Only one hardware.motors array group is supported by Motor310 runtime generation")
    if len(encoder_array_groups) > 1:
        raise ConfigError("Only one hardware.encoders array group is supported by Motor310 runtime generation")
    motor_array_name = next(iter(motor_array_groups), None)
    encoder_array_name = next(iter(encoder_array_groups), None)
    chassis_motor_array_enabled = motor_array_name is not None
    chassis_encoder_array_enabled = encoder_array_name is not None
    motor_array_ident = to_identifier(motor_array_name) if motor_array_name else "Chassis"
    encoder_array_ident = to_identifier(encoder_array_name) if encoder_array_name else "Chassis"
    encoder_indexes = {
        name: index
        for index, name in enumerate(encoders.keys())
    }

    lines = []
    lines.append("// Generated by src/Tools/script/yaml_to_config.py.")
    lines.append(f"// Source: {source_path.as_posix()}")
    lines.append("#ifndef ROBOT_RUNTIME_HPP")
    lines.append("#define ROBOT_RUNTIME_HPP")
    lines.append("")
    lines.append('#include "pid.hpp"')
    lines.append('#include "filter.hpp"')
    lines.append('#include "DifferentialDrive.hpp"')
    lines.append('#include "tim.h"')
    lines.append('#include "drv_pwm.hpp"')
    lines.append('#include "encoder.hpp"')
    lines.append('#include "310Motor.hpp"')
    lines.append('#include "drv_gpio.hpp"')
    lines.append('#include "button.hpp"')
    lines.append('#include "led.hpp"')
    lines.append('#include "buzzer.hpp"')
    lines.append('#include "oled.hpp"')
    lines.append('#include "drv_uart.hpp"')
    lines.append('#include "usart.h"')
    if oled:
        lines.append('#include "i2c.h"')
    lines.append('#include "robot_config.hpp"')
    lines.append("")

    for name, uart in uart_map.items():
        callback_name = uart.get("rx_callback", "")
        if callback_name != "":
            lines.append(
                f"void {callback_name}(DRV::UART::UartId id, const DRV::UART::UartData &data);"
            )
    if uart_map:
        lines.append("")

    lines.append("namespace RobotRuntime")
    lines.append("{")

    if buttons:
        sorted_buttons = list(buttons.items())
        lines.append(f"    inline DRV::GPIO::HalGpio (&ButtonPins())[{len(sorted_buttons)}]")
        lines.append("    {")
        lines.append(f"        static DRV::GPIO::HalGpio pins[{len(sorted_buttons)}] =")
        lines.append("        {")
        for name, button in sorted_buttons:
            lines.append(
                f"            DRV::GPIO::HalGpio({cpp_gpio_pin_expr(button['pin'], f'hardware.buttons.{name}') }),"
            )
        lines.append("        };")
        lines.append("")
        lines.append("        return pins;")
        lines.append("    }")
        lines.append("")

        lines.append(f"    inline BSP::BUTTON::Button (&Buttons())[{len(sorted_buttons)}]")
        lines.append("    {")
        lines.append(f"        static BSP::BUTTON::Button buttons[{len(sorted_buttons)}] =")
        lines.append("        {")
        for index, (name, button) in enumerate(sorted_buttons):
            lines.append(
                "            BSP::BUTTON::Button("
                f"ButtonPins()[{index}], "
                f"{cpp_bool(button.get('active_low', True))}"
                "),"
            )
        lines.append("        };")
        lines.append("")
        lines.append("        return buttons;")
        lines.append("    }")
        lines.append("")

    if leds:
        sorted_leds = list(leds.items())
        lines.append(f"    inline DRV::GPIO::HalGpio (&LedPins())[{len(sorted_leds)}]")
        lines.append("    {")
        lines.append(f"        static DRV::GPIO::HalGpio pins[{len(sorted_leds)}] =")
        lines.append("        {")
        for name, led in sorted_leds:
            lines.append(
                f"            DRV::GPIO::HalGpio({cpp_gpio_pin_expr(led['pin'], f'hardware.leds.{name}') }),"
            )
        lines.append("        };")
        lines.append("")
        lines.append("        return pins;")
        lines.append("    }")
        lines.append("")

        lines.append(f"    inline BSP::LED::Led (&Leds())[{len(sorted_leds)}]")
        lines.append("    {")
        lines.append(f"        static BSP::LED::Led leds[{len(sorted_leds)}] =")
        lines.append("        {")
        for index, (name, led) in enumerate(sorted_leds):
            lines.append(
                "            BSP::LED::Led("
                f"LedPins()[{index}], "
                f"{cpp_bool(led.get('active_low', False))}"
                "),"
            )
        lines.append("        };")
        lines.append("")
        lines.append("        return leds;")
        lines.append("    }")
        lines.append("")

    if buzzer:
        lines.append("    inline DRV::GPIO::HalGpio &BuzzerPin()")
        lines.append("    {")
        lines.append(
            f"        static DRV::GPIO::HalGpio pin({cpp_gpio_pin_expr(buzzer['pin'], 'hardware.buzzer')});"
        )
        lines.append("        return pin;")
        lines.append("    }")
        lines.append("")

        lines.append("    inline BSP::Buzzer::Buzzer &Buzzer()")
        lines.append("    {")
        lines.append(
            f"        static BSP::Buzzer::Buzzer buzzer(BuzzerPin(), {cpp_bool(buzzer.get('active_low', False))});"
        )
        lines.append("        return buzzer;")
        lines.append("    }")
        lines.append("")

    if oled:
        i2c_handle = cpp_symbol(oled["i2c_handle"])
        lines.append("    inline BSP::OLED::Oled &Oled()")
        lines.append("    {")
        lines.append(
            f"        static BSP::OLED::Oled oled({i2c_handle}, RobotConfig::kOled.address);"
        )
        lines.append("        return oled;")
        lines.append("    }")
        lines.append("")

    for array_name, items in pid_array_groups.items():
        array_ident = to_identifier(array_name)
        sorted_items = sorted(items, key=lambda item: wheel_order_key(item[1]))
        lines.append(f"    inline ALG::PID::PID (&{array_ident}Pids())[{len(sorted_items)}]")
        lines.append("    {")
        lines.append(f"        static ALG::PID::PID pids[{len(sorted_items)}] =")
        lines.append("        {")
        for _, pid_name in sorted_items:
            pid_ident = to_identifier(pid_name)
            lines.append(f"            ALG::PID::PID(RobotConfig::kPid{pid_ident}),")
        lines.append("        };")
        lines.append("")
        lines.append("        return pids;")
        lines.append("    }")
        lines.append("")

    for name in pid_map.keys():
        if name in pid_names_in_arrays:
            continue

        ident = to_identifier(name)
        lines.append(f"    inline ALG::PID::PID &{ident}Pid()")
        lines.append("    {")
        lines.append(
            f"        static ALG::PID::PID pid(RobotConfig::kPid{ident});"
        )
        lines.append("        return pid;")
        lines.append("    }")
        lines.append("")

    for array_name, items in filter_array_groups.items():
        sorted_items = sorted(items, key=lambda item: item[0])
        first_filter = filters[sorted_items[0][1]]
        array_ident = to_identifier(array_name)
        if first_filter["type"] == "low_pass":
            lines.append(f"    inline ALG::Filter::LowPassFilter (&{array_ident}LowPassFilters())[{len(sorted_items)}]")
            lines.append("    {")
            lines.append(f"        static ALG::Filter::LowPassFilter filters[{len(sorted_items)}] =")
            lines.append("        {")
            for _, filter_name in sorted_items:
                filter_ident = to_identifier(filter_name)
                lines.append(f"            ALG::Filter::LowPassFilter(RobotConfig::kFilter{filter_ident}),")
            lines.append("        };")
            lines.append("")
            lines.append("        return filters;")
            lines.append("    }")
            lines.append("")
        elif first_filter["type"] == "td":
            lines.append(f"    inline ALG::Filter::TDFilter (&{array_ident}TdFilters())[{len(sorted_items)}]")
            lines.append("    {")
            lines.append(f"        static ALG::Filter::TDFilter filters[{len(sorted_items)}] =")
            lines.append("        {")
            for _, filter_name in sorted_items:
                filter_ident = to_identifier(filter_name)
                lines.append(f"            ALG::Filter::TDFilter(RobotConfig::kFilter{filter_ident}),")
            lines.append("        };")
            lines.append("")
            lines.append("        return filters;")
            lines.append("    }")
            lines.append("")

    for name, filter_config in filters.items():
        if name in filter_names_in_arrays:
            continue

        ident = to_identifier(name)
        if filter_config["type"] == "low_pass":
            lines.append(f"    inline ALG::Filter::LowPassFilter &{ident}LowPassFilter()")
            lines.append("    {")
            lines.append(
                f"        static ALG::Filter::LowPassFilter filter(RobotConfig::kFilter{ident});"
            )
            lines.append("        return filter;")
            lines.append("    }")
            lines.append("")
        elif filter_config["type"] == "td":
            lines.append(f"    inline ALG::Filter::TDFilter &{ident}TdFilter()")
            lines.append("    {")
            lines.append(
                f"        static ALG::Filter::TDFilter filter(RobotConfig::kFilter{ident});"
            )
            lines.append("        return filter;")
            lines.append("    }")
            lines.append("")

    if chassis_ik["type"] == "differential_drive":
        lines.append("    inline ALG::ChassisIK::Diff_IK &ChassisIK()")
        lines.append("    {")
        lines.append(
            "        static ALG::ChassisIK::Diff_IK ik(RobotConfig::kChassisIKConfig);"
        )
        lines.append("        return ik;")
        lines.append("    }")
        lines.append("")

    if chassis_encoder_array_enabled:
        sorted_encoder_items = sorted(
            encoder_array_groups[encoder_array_name],
            key=lambda item: wheel_order_key(item[1]),
        )
        lines.append(f"    inline BSP::ENCODER::HALEncoder (&{encoder_array_ident}EncoderHal())[{len(sorted_encoder_items)}]")
        lines.append("    {")
        lines.append(f"        static BSP::ENCODER::HALEncoder encoders[{len(sorted_encoder_items)}] =")
        lines.append("        {")
        for _, encoder_name in sorted_encoder_items:
            encoder = encoders[encoder_name]
            lines.append(f"            BSP::ENCODER::HALEncoder(&{cpp_symbol(encoder['timer'])}),")
        lines.append("        };")
        lines.append("")
        lines.append("        return encoders;")
        lines.append("    }")
        lines.append("")

        lines.append(f"    inline BSP::ENCODER::EncoderData (&{encoder_array_ident}EncoderData())[{len(sorted_encoder_items)}]")
        lines.append("    {")
        lines.append(f"        static BSP::ENCODER::EncoderData data[{len(sorted_encoder_items)}] =")
        lines.append("        {")
        motor_for_encoder = {motor["encoder"]: motor for _, motor in motors_by_index}
        for index, (_, encoder_name) in enumerate(sorted_encoder_items):
            motor = motor_for_encoder[encoder_name]
            encoder_index = encoder_indexes[encoder_name]
            pid_ident = to_identifier(motor["speed_pid"])
            lines.append("            BSP::ENCODER::EncoderData(")
            lines.append(f"                {encoder_array_ident}EncoderHal()[{index}],")
            lines.append(f"                RobotConfig::kEncoders[{encoder_index}].cpr,")
            lines.append(f"                RobotConfig::kPid{pid_ident}.T")
            lines.append("            ),")
        lines.append("        };")
        lines.append("")
        lines.append("        return data;")
        lines.append("    }")
        lines.append("")
    else:
        for _, motor in motors_by_index:
            encoder_name = motor["encoder"]
            encoder = encoders[encoder_name]
            encoder_ident = to_identifier(encoder_name)
            encoder_index = encoder_indexes[encoder_name]
            pid_ident = to_identifier(motor["speed_pid"])

            lines.append(f"    inline BSP::ENCODER::HALEncoder &{encoder_ident}Hal()")
            lines.append("    {")
            lines.append(
                f"        static BSP::ENCODER::HALEncoder encoder(&{cpp_symbol(encoder['timer'])});"
            )
            lines.append("        return encoder;")
            lines.append("    }")
            lines.append("")
            lines.append(f"    inline BSP::ENCODER::EncoderData &{encoder_ident}Data()")
            lines.append("    {")
            lines.append(
                f"        static BSP::ENCODER::EncoderData data({encoder_ident}Hal(), "
                f"RobotConfig::kEncoders[{encoder_index}].cpr, "
                f"RobotConfig::kPid{pid_ident}.T);"
            )
            lines.append("        return data;")
            lines.append("    }")
            lines.append("")

    if chassis_motor_array_enabled:
        sorted_motor_items = sorted(
            motor_array_groups[motor_array_name],
            key=lambda item: wheel_order_key(item[1]),
        )
        lines.append(f"    inline DRV::PWM::HalPwmChannel (&{motor_array_ident}PwmA())[{len(sorted_motor_items)}]")
        lines.append("    {")
        lines.append(f"        static DRV::PWM::HalPwmChannel pwms[{len(sorted_motor_items)}] =")
        lines.append("        {")
        for _, motor_name in sorted_motor_items:
            motor = motors[motor_name]
            pwm_a = motor["pwm_a"]
            lines.append(
                f"            DRV::PWM::HalPwmChannel(&{cpp_symbol(pwm_a['timer'])}, "
                f"{cpp_symbol(pwm_a['channel'])}),"
            )
        lines.append("        };")
        lines.append("")
        lines.append("        return pwms;")
        lines.append("    }")
        lines.append("")

        lines.append(f"    inline DRV::PWM::HalPwmChannel (&{motor_array_ident}PwmB())[{len(sorted_motor_items)}]")
        lines.append("    {")
        lines.append(f"        static DRV::PWM::HalPwmChannel pwms[{len(sorted_motor_items)}] =")
        lines.append("        {")
        for _, motor_name in sorted_motor_items:
            motor = motors[motor_name]
            pwm_b = motor["pwm_b"]
            lines.append(
                f"            DRV::PWM::HalPwmChannel(&{cpp_symbol(pwm_b['timer'])}, "
                f"{cpp_symbol(pwm_b['channel'])}),"
            )
        lines.append("        };")
        lines.append("")
        lines.append("        return pwms;")
        lines.append("    }")
        lines.append("")
    else:
        for name, motor in motors_by_index:
            ident = to_identifier(name)
            pwm_a = motor["pwm_a"]
            pwm_b = motor["pwm_b"]

            lines.append(f"    inline DRV::PWM::HalPwmChannel &{ident}PwmA()")
            lines.append("    {")
            lines.append(
                "        static DRV::PWM::HalPwmChannel pwm("
                f"&{cpp_symbol(pwm_a['timer'])}, "
                f"{cpp_symbol(pwm_a['channel'])}"
                ");"
            )
            lines.append("        return pwm;")
            lines.append("    }")
            lines.append("")
            lines.append(f"    inline DRV::PWM::HalPwmChannel &{ident}PwmB()")
            lines.append("    {")
            lines.append(
                "        static DRV::PWM::HalPwmChannel pwm("
                f"&{cpp_symbol(pwm_b['timer'])}, "
                f"{cpp_symbol(pwm_b['channel'])}"
                ");"
            )
            lines.append("        return pwm;")
            lines.append("    }")
            lines.append("")

    if uart_map:
        lines.append("    inline bool UartTx(DRV::UART::UartId id, const uint8_t *data, uint16_t len)")
        lines.append("    {")
        lines.append("        switch (id)")
        lines.append("        {")
        for name, uart in uart_map.items():
            uart_ident = to_identifier(uart["logical_id"])
            handle = cpp_symbol(uart["handle"])
            tx_mode = uart["tx_mode"]
            lines.append(f"            case DRV::UART::UartId::{uart_ident}:")
            if tx_mode == "dma":
                lines.append(f"                return HAL_UART_Transmit_DMA(&{handle}, data, len) == HAL_OK;")
            elif tx_mode == "it":
                lines.append(f"                return HAL_UART_Transmit_IT(&{handle}, data, len) == HAL_OK;")
            else:
                lines.append(f"                return HAL_UART_Transmit(&{handle}, data, len, 10U) == HAL_OK;")
        lines.append("            default:")
        lines.append("                return false;")
        lines.append("        }")
        lines.append("    }")
        lines.append("")

        lines.append("    inline bool UartRx(DRV::UART::UartId id, uint8_t *buffer, uint16_t len)")
        lines.append("    {")
        lines.append("        switch (id)")
        lines.append("        {")
        for name, uart in uart_map.items():
            uart_ident = to_identifier(uart["logical_id"])
            handle = cpp_symbol(uart["handle"])
            rx_mode = uart["rx_mode"]
            lines.append(f"            case DRV::UART::UartId::{uart_ident}:")
            if rx_mode == "idle_dma":
                lines.append(f"                return HAL_UARTEx_ReceiveToIdle_DMA(&{handle}, buffer, len) == HAL_OK;")
            elif rx_mode == "dma":
                lines.append(f"                return HAL_UART_Receive_DMA(&{handle}, buffer, len) == HAL_OK;")
            elif rx_mode == "it":
                lines.append(f"                return HAL_UART_Receive_IT(&{handle}, buffer, len) == HAL_OK;")
            else:
                lines.append(f"                return HAL_UART_Receive(&{handle}, buffer, len, 10U) == HAL_OK;")
        lines.append("            default:")
        lines.append("                return false;")
        lines.append("        }")
        lines.append("    }")
        lines.append("")

        for name, uart in uart_map.items():
            uart_ident = to_identifier(uart["logical_id"])
            rx_buffer_size = as_int(uart["rx_buffer_size"])
            lines.append(f"    inline uint8_t (&{uart_ident}RxBuffer())[{rx_buffer_size}]")
            lines.append("    {")
            lines.append(f"        static uint8_t buffer[{rx_buffer_size}] = {{}};")
            lines.append("        return buffer;")
            lines.append("    }")
            lines.append("")

        lines.append("    inline void InitUarts()")
        lines.append("    {")
        lines.append("        auto &uart = DRV::UART::UartManager::Instance();")
        lines.append("        uart.Init();")
        lines.append("        uart.RegisterTxFunction(UartTx);")
        lines.append("        uart.RegisterRxFunction(UartRx);")
        for name, uart in uart_map.items():
            callback_name = uart.get("rx_callback", "")
            if callback_name != "":
                uart_ident = to_identifier(uart["logical_id"])
                lines.append(
                    f"        uart.RegisterRxCallback(DRV::UART::UartId::{uart_ident}, {callback_name});"
                )
            uart_ident = to_identifier(uart["logical_id"])
            lines.append(
                f"        uart.Receive(DRV::UART::UartId::{uart_ident}, {uart_ident}RxBuffer(), sizeof({uart_ident}RxBuffer()));"
            )
        lines.append("    }")
        lines.append("")

        lines.append("    inline void OnUartRxEvent(UART_HandleTypeDef *huart, uint16_t size)")
        lines.append("    {")
        lines.append("        auto &manager = DRV::UART::UartManager::Instance();")
        for name, uart in uart_map.items():
            uart_ident = to_identifier(uart["logical_id"])
            handle = cpp_symbol(uart["handle"])
            lines.append(f"        if (huart == &{handle})")
            lines.append("        {")
            lines.append(
                f"            manager.Callback(DRV::UART::UartId::{uart_ident}, {uart_ident}RxBuffer(), size);"
            )
            lines.append(
                f"            manager.Receive(DRV::UART::UartId::{uart_ident}, {uart_ident}RxBuffer(), sizeof({uart_ident}RxBuffer()));"
            )
            lines.append("            return;")
            lines.append("        }")
        lines.append("    }")
        lines.append("")

    lines.append("    inline BSP::Motor::_310::MotorConfig (&ChassisMotorConfigs())[4]")
    lines.append("    {")
    lines.append("        static BSP::Motor::_310::MotorConfig configs[4] =")
    lines.append("        {")
    for index, (name, motor) in enumerate(motors_by_index):
        ident = to_identifier(name)
        encoder_ident = to_identifier(motor["encoder"])
        if "left_front" in name:
            motor_id = "LeftForward"
        elif "right_front" in name:
            motor_id = "RightForward"
        elif "left_back" in name:
            motor_id = "LeftBackward"
        elif "right_back" in name:
            motor_id = "RightBackward"
        else:
            motor_id = "LeftForward"
        pwm_a_expr = (
            f"&{motor_array_ident}PwmA()[{index}]"
            if chassis_motor_array_enabled
            else f"&{ident}PwmA()"
        )
        pwm_b_expr = (
            f"&{motor_array_ident}PwmB()[{index}]"
            if chassis_motor_array_enabled
            else f"&{ident}PwmB()"
        )
        encoder_expr = (
            f"&{encoder_array_ident}EncoderData()[{index}]"
            if chassis_encoder_array_enabled
            else f"&{encoder_ident}Data()"
        )

        lines.append("            {")
        lines.append(f"                BSP::Motor::_310::MotorId::{motor_id},")
        lines.append(f"                {pwm_a_expr},")
        lines.append(f"                {pwm_b_expr},")
        lines.append(f"                {encoder_expr},")
        lines.append(
            "                BSP::Motor::_310::Parameters("
            f"RobotConfig::kMotors[{index}].reduction_ratio"
            ")"
        )
        lines.append("            },")
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
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--uart-output", type=Path)
    parser.add_argument("--messages-output", type=Path)
    parser.add_argument("--runtime-output", type=Path)
    args = parser.parse_args()

    output_root = args.input.resolve().parent.parent
    output_dir = output_root / "src" / "Tools" / "generated"
    output = args.output or output_dir / "robot_config.hpp"
    uart_output = args.uart_output or output_dir / "robot_uart.hpp"
    messages_output = args.messages_output or output_dir / "robot_messages.hpp"
    runtime_output = args.runtime_output or output_dir / "robot_runtime.hpp"

    config = load_yaml_subset(args.input)
    validate_config(config)
    uart_header = generate_uart_header(config, args.input)
    header = generate_header(config, args.input)
    messages_header = generate_messages_header(config, args.input)
    runtime_header = generate_runtime_header(config, args.input)

    uart_output.parent.mkdir(parents=True, exist_ok=True)
    uart_output.write_text(uart_header, encoding="utf-8", newline="\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header, encoding="utf-8", newline="\n")
    messages_output.parent.mkdir(parents=True, exist_ok=True)
    messages_output.write_text(messages_header, encoding="utf-8", newline="\n")
    runtime_output.parent.mkdir(parents=True, exist_ok=True)
    runtime_output.write_text(runtime_header, encoding="utf-8", newline="\n")
    print(f"generated: {uart_output}")
    print(f"generated: {output}")
    print(f"generated: {messages_output}")
    print(f"generated: {runtime_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
