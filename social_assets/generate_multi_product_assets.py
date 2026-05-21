from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent
SCREEN_DIR = OUT / "screenshots"
W, H = 1080, 1440
REPO_URL = "github.com/leisymqaz/lumerical-fdtd-mcp"

FONT_PATHS = [
    r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


F_TITLE = font(62)
F_H = font(40)
F_BODY = font(30)
F_SMALL = font(24)
F_MONO = font(28)


def fit_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, max_width: int, base_font, fill) -> None:
    font_obj = base_font
    size = getattr(base_font, "size", 28)
    while draw.textbbox((0, 0), text, font=font_obj)[2] > max_width and size > 18:
        size -= 2
        font_obj = font(size)
    draw.text(xy, text, font=font_obj, fill=fill)


def paste_cover(base: Image.Image, src: Image.Image, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    sw, sh = src.size
    scale = max(bw / sw, bh / sh)
    resized = src.resize((int(sw * scale), int(sh * scale)), Image.Resampling.LANCZOS)
    rx, ry = resized.size
    crop = resized.crop(((rx - bw) // 2, (ry - bh) // 2, (rx + bw) // 2, (ry + bh) // 2))
    base.paste(crop, (x0, y0))


def paste_contain(base: Image.Image, src: Image.Image, box: tuple[int, int, int, int], bg=(255, 255, 255)) -> None:
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    base.paste(Image.new("RGB", (bw, bh), bg), (x0, y0))
    sw, sh = src.size
    scale = min(bw / sw, bh / sh)
    resized = src.resize((int(sw * scale), int(sh * scale)), Image.Resampling.LANCZOS)
    rx, ry = resized.size
    base.paste(resized, (x0 + (bw - rx) // 2, y0 + (bh - ry) // 2))


def footer(draw: ImageDraw.ImageDraw, dark: bool = True) -> None:
    main = (245, 247, 250) if dark else (17, 24, 39)
    muted = (154, 204, 185) if dark else (70, 86, 105)
    draw.text((64, H - 168), "GitHub", font=F_H, fill=muted)
    fit_text(draw, (64, H - 108), REPO_URL, 930, F_MONO, main)
    draw.text((64, H - 58), "Codex x Lumerical MCP", font=F_SMALL, fill=muted)


def make_cover(screens: dict[str, Image.Image]) -> None:
    img = Image.new("RGB", (W, H), (15, 22, 34))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 18), fill=(42, 157, 143))
    draw.rectangle((0, H - 18, W, H), fill=(42, 157, 143))
    draw.text((64, 72), "Lumerical MCP", font=F_TITLE, fill=(245, 247, 250))
    draw.text((66, 158), "Codex 接管四个产品窗口", font=F_H, fill=(185, 225, 212))

    boxes = {
        "FDTD": (64, 270, 520, 610),
        "MODE": (560, 270, 1016, 610),
        "INTERCONNECT": (64, 660, 520, 1000),
        "DEVICE": (560, 660, 1016, 1000),
    }
    keys = {"FDTD": "fdtd", "MODE": "mode", "INTERCONNECT": "interconnect", "DEVICE": "device"}
    for label, box in boxes.items():
        x0, y0, x1, y1 = box
        draw.rounded_rectangle((x0, y0, x1, y1), radius=16, fill=(245, 247, 250), outline=(42, 157, 143), width=3)
        paste_cover(img, screens[keys[label]], (x0 + 14, y0 + 52, x1 - 14, y1 - 14))
        draw.text((x0 + 18, y0 + 14), label, font=F_SMALL, fill=(17, 24, 39))

    footer(draw, dark=True)
    img.save(OUT / "xhs_multi_card_1.png", quality=95)


def make_product_card(name: str, subtitle: str, bullets: list[str], screen: Image.Image, filename: str, accent) -> None:
    img = Image.new("RGB", (W, H), (247, 249, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 18), fill=accent)
    draw.text((64, 72), name, font=F_TITLE, fill=(17, 24, 39))
    fit_text(draw, (66, 158), subtitle, 950, F_H, accent)
    draw.rounded_rectangle((64, 270, 1016, 940), radius=18, fill=(255, 255, 255), outline=accent, width=3)
    paste_contain(img, screen, (88, 304, 992, 908), bg=(255, 255, 255))

    y = 990
    for bullet in bullets:
        draw.ellipse((72, y + 12, 90, y + 30), fill=accent)
        fit_text(draw, (108, y), bullet, 880, F_BODY, (17, 24, 39))
        y += 54

    footer(draw, dark=False)
    img.save(OUT / filename, quality=95)


def main() -> None:
    screens = {
        "fdtd": Image.open(SCREEN_DIR / "fdtd_printwindow.png").convert("RGB"),
        "mode": Image.open(SCREEN_DIR / "mode_printwindow.png").convert("RGB"),
        "interconnect": Image.open(SCREEN_DIR / "interconnect_printwindow.png").convert("RGB"),
        "device": Image.open(SCREEN_DIR / "device_printwindow.png").convert("RGB"),
    }
    make_cover(screens)
    make_product_card(
        "FDTD",
        "Si nanoblock + SiO2 substrate",
        ["周期边界、平面波源、T/R monitors", "保存为 .fsp，可直接打开复查", "旧 fdtd_* MCP 工具保持兼容"],
        screens["fdtd"],
        "xhs_multi_card_2_fdtd.png",
        (34, 93, 174),
    )
    make_product_card(
        "MODE",
        "Si waveguide eigenmode setup",
        ["建立 Si/SiO2 波导横截面", "添加 FDE 求模区域", "保存为 .lms"],
        screens["mode"],
        "xhs_multi_card_3_mode.png",
        (42, 157, 143),
    )
    make_product_card(
        "INTERCONNECT",
        "Laser - waveguide - OSA circuit",
        ["创建 CW Laser、Straight Waveguide、OSA", "自动连接 input/output ports", "保存为 .icp"],
        screens["interconnect"],
        "xhs_multi_card_4_interconnect.png",
        (181, 94, 40),
    )
    make_product_card(
        "DEVICE",
        "CHARGE region demo",
        ["创建器件几何和 CHARGE solver", "添加局部 charge mesh", "保存为 .ldev"],
        screens["device"],
        "xhs_multi_card_5_device.png",
        (120, 88, 166),
    )

    caption = """标题：让 Codex 接管 Lumerical：FDTD / MODE / INTERCONNECT / DEVICE

正文：
继续把本地 Lumerical MCP 扩展成多产品版本。现在 Codex 可以通过同一个 MCP 桥接 lumapi，分别打开 FDTD、MODE、INTERCONNECT、DEVICE 会话，执行 Lumerical script，保存/加载工程文件。

这次实操验证了四个最小示例：
1. FDTD：Si nanoblock + SiO2 substrate，带平面波源和 T/R monitors
2. MODE：Si/SiO2 波导 + FDE 求模区域
3. INTERCONNECT：CW Laser - Straight Waveguide - OSA 光路
4. DEVICE：简单器件几何 + CHARGE solver + mesh

GitHub：
https://github.com/leisymqaz/lumerical-fdtd-mcp

#Lumerical #FDTD #MODE #INTERCONNECT #DEVICE #MCP #Codex #光子仿真 #科研工具
"""
    (OUT / "xhs_multi_caption.txt").write_text(caption, encoding="utf-8")


if __name__ == "__main__":
    main()
