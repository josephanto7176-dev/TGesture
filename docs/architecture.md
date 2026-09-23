# Architecture

## Gesture math

For two contacts `A` and `B`, calculate the vector from `A` to `B`:

```text
v = B - A
```

For the previous and current frames, calculate the signed change in angle:

```text
delta = atan2(cross(previous, current), dot(previous, current))
```

Normalize the result to `[-180, 180]`, ignore small changes in the dead zone, and accumulate the remaining degrees until `degreesPerAction` is reached.

## Windows input boundary

The utility should own a hidden message window and register for raw input with `RIDEV_INPUTSINK`. The HID adapter must identify the Precision Touchpad collection and decode contact count, contact identifiers, and X/Y coordinates from its reports. Report layouts can vary, so the adapter must inspect the HID preparsed data instead of assuming fixed byte offsets.

If the laptop driver does not expose usable raw reports, the utility should report that condition clearly and stop. It must not install a kernel filter silently.

## Output boundary

There is no reliable output that rotates an image in every Windows application. Output adapters should be explicit:

- Native application command, where the application exposes one.
- UI Automation, where the target control is accessible.
- Configurable synthetic input as a last resort.

The foreground process should be matched against an allow-list. Rotation output should be disabled by default until a profile is configured.
