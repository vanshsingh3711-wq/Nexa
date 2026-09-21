from PIL import Image

def remove_background(img_path, out_path, tolerance=30):
    img = Image.open(img_path).convert("RGBA")
    datas = img.getdata()

    new_data = []
    # The background is dark gray/black (approx rgb(24, 24, 24) in the corners)
    # Let's sample the top-left corner
    bg_color = datas[0]
    
    for item in datas:
        # Check if color is close to background color
        if abs(item[0] - bg_color[0]) < tolerance and \
           abs(item[1] - bg_color[1]) < tolerance and \
           abs(item[2] - bg_color[2]) < tolerance:
            new_data.append((255, 255, 255, 0)) # Transparent
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(out_path, "PNG")

remove_background("backend/ui/assets/cute_robot.png", "backend/ui/assets/cute_robot_transparent.png")
