from PIL import Image

img = Image.new('RGBA', (512, 512), color=(0, 0, 0, 0))
img.save('nexus/src-tauri/icons/icon.png')
for size in [32, 128, 256, 512]:
    img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    img.save(f'nexus/src-tauri/icons/{size}x{size}.png')
print("Generated icons")
