#!/bin/bash
# Script to help flash MicroPython firmware to Raspberry Pi Pico W

echo "=== Raspberry Pi Pico W Flash Helper ==="
echo ""
echo "This script helps you upload your firmware to the Pico W."
echo ""
echo "Instructions:"
echo "1. Hold the BOOTSEL button on your Pico W"
echo "2. Connect USB cable to Mac"
echo "3. A drive called 'RPI-RP2' should appear"
echo "4. When prompted, drag and drop main.py onto the RPI-RP2 drive"
echo ""

# Check if micropython firmware exists
MICRO_PATH="$HOME/Downloads/micropython-rp2-pico-w.uf2"
if [ -f "$MICRO_PATH" ]; then
    echo "Found MicroPython firmware at: $MICRO_PATH"
    echo "To flash this, drag it onto the RPI-RP2 drive when in BOOTSEL mode."
else
    echo "MicroPython firmware not found at: $MICRO_PATH"
    echo ""
    echo "Download from: https://micropython.org/download/rp2-pico-w/"
fi

echo ""
echo "=== To upload main.py ==="
echo "1. Put Pico in BOOTSEL mode (hold BOOTSEL, plug in USB)"
echo "2. When 'RPI-RP2' drive appears, copy these files:"
echo "   - main.py"
echo "   - config.py"
echo ""
echo "=== To upload only main.py ==="
echo "cp /home/adam/Development/r-pi-pico-temperature/main.py ~/Desktop/"
echo "Then drag main.py from Desktop to RPI-RP2 drive"
