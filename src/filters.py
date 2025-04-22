import random
from pathlib import Path
from PIL import Image, ImageEnhance

OUTPUT_DIR = Path.cwd() / "images"



def none_filter(frame_path: Path) -> Path:
    """Retorna a imagem original sem aplicar nenhum filtro."""
    return frame_path


def two_panels(frame_path1: Path, frame_path2: Path) -> Path:
    with Image.open(frame_path1) as img1, Image.open(frame_path2) as img2:
        image_width, image_height = img1.size
        img3 = Image.new("RGB", (image_width, image_height * 2))
        img3.paste(img1, (0, 0))
        img3.paste(img2, (0, image_height))

        output_path = OUTPUT_DIR / "_two_panels.jpg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img3.save(output_path)
        return output_path


def mirror(frame_path) -> Path:
    """Espelha aleatoriamente o lado esquerdo ou direito da imagem."""
    with Image.open(frame_path) as img:
        width, height = img.size
        output_img = Image.new("RGB", (width, height))

        if random.choice([True, False]):
            half = img.crop((0, 0, width // 2, height))
            mirrored_half = half.transpose(Image.FLIP_LEFT_RIGHT)
            output_img.paste(half, (0, 0))
            output_img.paste(mirrored_half, (width // 2, 0))
        else:
            half = img.crop((width // 2, 0, width, height))
            mirrored_half = half.transpose(Image.FLIP_LEFT_RIGHT)
            output_img.paste(mirrored_half, (0, 0))
            output_img.paste(half, (width // 2, 0))

    output_path = OUTPUT_DIR / "_mirror.jpg"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_img.save(output_path)
    return output_path


def brightness_contrast(frame_path: Path, brightness: float = 0.8, contrast: float = 1.5) -> Path:
    """Aplica um filtro de brilho e contraste a uma imagem."""
    input_path = Path(frame_path)

    if not input_path.exists():
        return None
    
    output_path = OUTPUT_DIR / "_brightness_contrast.jpg"

    with Image.open(input_path) as img:
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        img.save(output_path)

    return output_path


def negative(frame_path) -> Path:
    """Aplica um filtro negativo."""
    with Image.open(frame_path) as img:
        output_img = img.convert("RGB").point(lambda x: 255 - x)

    output_path = OUTPUT_DIR / "_negative.jpg"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_img.save(output_path)

    return output_path


# def warp_in(frame_path) -> Path:
#     with Image.open(frame_path) as img:
#         output_img = img.convert("RGB")

#     output_path = OUTPUT_DIR / "_warp_in.jpg"
#     output_path.parent.mkdir(parents=True, exist_ok=True)
#     output_img.save(output_path)

#     return output_path


# def warp_out(frame_path: Path) -> Path:
#     with Image.open(frame_path) as img:
#         output_img = img.convert("RGB")

#     output_path = OUTPUT_DIR / "_warp_out.jpg"
#     output_path.parent.mkdir(parents=True, exist_ok=True)
#     output_img.save(output_path)

#     return output_path


filter_registry = {
    'none_filter': none_filter,
    'two_panels': two_panels,
    'mirror': mirror,
    'negative': negative,
    # 'warp_in': warp_in,
    # 'warp_out': warp_out,
    'brightness_contrast': brightness_contrast
}


def select_filter(configs: dict) -> callable:
    """
    Select an enabled filter based on the configuration and their respective weights.
    """
    active_filters = {}
    filters_config = configs.get("filters", {})
    
    for filter_name, filter_settings in filters_config.items():
        if isinstance(filter_settings, dict) and filter_settings.get("enabled", False):
            active_filters[filter_name] = filter_settings.get("percent", 0)

    if not active_filters:
        return filter_registry['none_filter']

    selected_filter = random.choices(
        list(active_filters.keys()), 
        weights=list(active_filters.values()), 
        k=1
    )[0]

    return filter_registry[selected_filter]
