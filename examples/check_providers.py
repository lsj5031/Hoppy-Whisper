"""Example script to check available ONNX Runtime providers."""

from app.transcriber import get_session_manager


def main() -> None:
    """Display available ONNX Runtime providers and device info."""
    print("=" * 60)
    print("ONNX Runtime Provider Detection")
    print("=" * 60)

    manager = get_session_manager()

    providers, options = manager.get_providers()
    print("\nSelected providers:")
    for i, (provider, opts) in enumerate(zip(providers, options)):
        print(f"  {i + 1}. {provider}")
        if opts:
            print(f"     Options: {opts}")

    devices = manager.get_device_info()
    print("\nDevice Information:")
    for device in devices:
        status = "✓" if device.available else "✗"
        print(f"  {status} {device.name}")
        if device.device_name:
            print(f"    Device: {device.device_name}")
        if device.error:
            print(f"    Error: {device.error}")

    print("\n" + "=" * 60)
    if "DmlExecutionProvider" in providers:
        print("DirectML GPU acceleration is available!")
    else:
        print("Using CPU inference (DirectML not available)")
    print("=" * 60)


if __name__ == "__main__":
    main()
