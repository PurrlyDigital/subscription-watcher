# Agent instructions

## Release a new version

Run the tests, build the ZIP, and verify the checksum as described in the
"Test and package" section of `README.md`.

### Replace the screenshot when the sidebar changes

If the release changes anything the sidebar shows, replace
`assets/subscription-sidebar.png` with a new screenshot before you build the
ZIP. Visible changes include row text, labels, symbols, countdown or time
formats, row order, and colors. Keep the old screenshot only when the release
has no visible change.

If you cannot take the screenshot yourself, ask the user for one. If the rows
changed, update the image's alt text in `README.md` to match.

### Remove metadata before you commit the screenshot

macOS screenshots contain EXIF data, capture details, and a display color
profile. Remove them before you commit the image. Keep only the `IHDR`, `PLTE`,
`tRNS`, `IDAT`, `IEND`, `sRGB`, and `gAMA` chunks.

This command copies a screenshot to the asset path and prints the chunks it
dropped. Replace `<screenshot.png>` with the screenshot's path.

```sh
/usr/bin/python3 - <screenshot.png> assets/subscription-sidebar.png <<'EOF'
import struct, sys
source, target = sys.argv[1:]
data = open(source, "rb").read()
if data[:8] != b"\x89PNG\r\n\x1a\n":
	sys.exit("not a PNG file")
keep = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND", b"sRGB", b"gAMA"}
chunks, dropped, index = [data[:8]], [], 8
while index < len(data):
	size, name = struct.unpack(">I4s", data[index:index + 8])
	chunk = data[index:index + 12 + size]
	if name in keep:
		chunks.append(chunk)
	else:
		dropped.append(name.decode())
	index += 12 + size
open(target, "wb").write(b"".join(chunks))
print("dropped:", dropped)
EOF
```

Open the result and confirm that it renders before you commit it.
