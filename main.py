
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from PIL import Image, ExifTags
from io import BytesIO


app = FastAPI(
    title="Photo EXIF Markdown API",
    description="写真の撮影情報を整理してMarkdown形式で返します",
    version="2.0.0"
)


def md(value):
    if value is None:
        return "-"

    return (
        str(value)
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def rational_to_float(value):
    try:
        return float(value)
    except Exception:
        return None


def format_number(value, digits=2):
    try:
        number = float(value)

        if number.is_integer():
            return str(int(number))

        return f"{number:.{digits}f}".rstrip("0").rstrip(".")

    except Exception:
        return str(value)


def format_exposure_time(value):
    try:
        seconds = float(value)

        if seconds <= 0:
            return str(value)

        if seconds >= 1:
            return f"{format_number(seconds, 2)} sec"

        denominator = round(1 / seconds)

        return f"1/{denominator} sec"

    except Exception:
        return str(value)


def format_aperture(value):
    try:
        return f"f/{format_number(float(value), 1)}"
    except Exception:
        return str(value)


def format_focal_length(value):
    try:
        return f"{format_number(float(value), 1)} mm"
    except Exception:
        return str(value)


def format_ev(value):
    try:
        number = float(value)

        if number > 0:
            return f"+{format_number(number, 2)} EV"

        return f"{format_number(number, 2)} EV"

    except Exception:
        return str(value)


def get_tag(dictionary, name):
    for tag_id, value in dictionary.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))

        if tag_name == name:
            return value

    return None


def gps_value(gps, tag_name):
    for tag_id, value in gps.items():

        name = ExifTags.GPSTAGS.get(
            tag_id,
            str(tag_id)
        )

        if name == tag_name:
            return value

    return None


def gps_to_decimal(value, ref):
    if not value:
        return None

    try:
        degrees = float(value[0])
        minutes = float(value[1])
        seconds = float(value[2])

        result = (
            degrees
            + minutes / 60
            + seconds / 3600
        )

        if ref in ["S", "W"]:
            result *= -1

        return round(result, 6)

    except Exception:
        return None


def add_row(markdown, name, value):
    if value is None:
        value = "-"

    markdown += (
        f"| {md(name)} | {md(value)} |\n"
    )

    return markdown


@app.get(
    "/",
    response_class=PlainTextResponse
)
async def root():

    text = (
        "# Photo EXIF REST API\n\n"
        "画像をPOSTすると撮影情報を"
        "Markdown形式で返します。\n\n"
        "## Endpoint\n\n"
        "`POST /exif`\n\n"
        "## Swagger UI\n\n"
        "`GET /docs`\n"
    )

    return PlainTextResponse(
        text,
        media_type="text/markdown; charset=utf-8"
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0"
    }


@app.post(
    "/exif",
    response_class=PlainTextResponse
)
async def get_exif(
    file: UploadFile = File(...)
):

    if not file.content_type:
        raise HTTPException(
            status_code=400,
            detail="Content-Typeがありません"
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="画像ファイルを指定してください"
        )

    try:
        image_data = await file.read()

        image = Image.open(
            BytesIO(image_data)
        )

        exif = image.getexif()

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"画像を読み込めませんでした: {e}"
        )


    # ----------------------------
    # EXIF IFD
    # ----------------------------

    exif_ifd = {}

    try:
        exif_ifd = exif.get_ifd(
            ExifTags.IFD.Exif
        )
    except Exception:
        pass


    # ----------------------------
    # GPS IFD
    # ----------------------------

    gps_ifd = {}

    try:
        gps_ifd = exif.get_ifd(
            ExifTags.IFD.GPSInfo
        )
    except Exception:
        pass


    # ----------------------------
    # Camera
    # ----------------------------

    make = get_tag(exif, "Make")
    model = get_tag(exif, "Model")
    software = get_tag(exif, "Software")


    # ----------------------------
    # Lens
    # ----------------------------

    lens_model = get_tag(
        exif_ifd,
        "LensModel"
    )

    if lens_model is None:
        lens_model = get_tag(
            exif,
            "LensModel"
        )


    focal_length = get_tag(
        exif_ifd,
        "FocalLength"
    )

    focal_35 = get_tag(
        exif_ifd,
        "FocalLengthIn35mmFilm"
    )


    # ----------------------------
    # Shooting
    # ----------------------------

    exposure_time = get_tag(
        exif_ifd,
        "ExposureTime"
    )

    f_number = get_tag(
        exif_ifd,
        "FNumber"
    )

    iso = get_tag(
        exif_ifd,
        "ISOSpeedRatings"
    )

    if iso is None:
        iso = get_tag(
            exif_ifd,
            "PhotographicSensitivity"
        )

    exposure_bias = get_tag(
        exif_ifd,
        "ExposureBiasValue"
    )

    exposure_program = get_tag(
        exif_ifd,
        "ExposureProgram"
    )

    metering_mode = get_tag(
        exif_ifd,
        "MeteringMode"
    )

    flash = get_tag(
        exif_ifd,
        "Flash"
    )

    white_balance = get_tag(
        exif_ifd,
        "WhiteBalance"
    )


    # ----------------------------
    # Date
    # ----------------------------

    datetime_original = get_tag(
        exif_ifd,
        "DateTimeOriginal"
    )

    datetime_digitized = get_tag(
        exif_ifd,
        "DateTimeDigitized"
    )

    datetime_general = get_tag(
        exif,
        "DateTime"
    )


    # ----------------------------
    # GPS
    # ----------------------------

    latitude = None
    longitude = None
    altitude = None

    if gps_ifd:

        latitude_raw = gps_value(
            gps_ifd,
            "GPSLatitude"
        )

        latitude_ref = gps_value(
            gps_ifd,
            "GPSLatitudeRef"
        )

        longitude_raw = gps_value(
            gps_ifd,
            "GPSLongitude"
        )

        longitude_ref = gps_value(
            gps_ifd,
            "GPSLongitudeRef"
        )

        altitude_raw = gps_value(
            gps_ifd,
            "GPSAltitude"
        )

        latitude = gps_to_decimal(
            latitude_raw,
            latitude_ref
        )

        longitude = gps_to_decimal(
            longitude_raw,
            longitude_ref
        )

        if altitude_raw is not None:
            try:
                altitude = (
                    f"{format_number(float(altitude_raw), 1)} m"
                )
            except Exception:
                altitude = str(altitude_raw)


    # ----------------------------
    # Markdown
    # ----------------------------

    markdown = "# Photo Information\n\n"


    # Camera

    markdown += "## Camera\n\n"
    markdown += "| Item | Value |\n"
    markdown += "|---|---|\n"

    markdown = add_row(
        markdown,
        "Manufacturer",
        make
    )

    markdown = add_row(
        markdown,
        "Camera",
        model
    )

    markdown = add_row(
        markdown,
        "Software",
        software
    )


    # Lens

    markdown += "\n## Lens\n\n"
    markdown += "| Item | Value |\n"
    markdown += "|---|---|\n"

    markdown = add_row(
        markdown,
        "Lens",
        lens_model
    )

    if focal_length is not None:
        focal_length = format_focal_length(
            focal_length
        )

    markdown = add_row(
        markdown,
        "Focal Length",
        focal_length
    )

    if focal_35 is not None:
        focal_35 = format_focal_length(
            focal_35
        )

    markdown = add_row(
        markdown,
        "35mm Equivalent",
        focal_35
    )


    # Shooting

    markdown += "\n## Shooting\n\n"
    markdown += "| Item | Value |\n"
    markdown += "|---|---|\n"

    if exposure_time is not None:
        exposure_time = format_exposure_time(
            exposure_time
        )

    markdown = add_row(
        markdown,
        "Shutter Speed",
        exposure_time
    )

    if f_number is not None:
        f_number = format_aperture(
            f_number
        )

    markdown = add_row(
        markdown,
        "Aperture",
        f_number
    )

    markdown = add_row(
        markdown,
        "ISO",
        iso
    )

    if exposure_bias is not None:
        exposure_bias = format_ev(
            exposure_bias
        )

    markdown = add_row(
        markdown,
        "Exposure Compensation",
        exposure_bias
    )

    markdown = add_row(
        markdown,
        "Exposure Program",
        exposure_program
    )

    markdown = add_row(
        markdown,
        "Metering Mode",
        metering_mode
    )

    markdown = add_row(
        markdown,
        "White Balance",
        white_balance
    )

    markdown = add_row(
        markdown,
        "Flash",
        flash
    )


    # Date

    markdown += "\n## Date\n\n"
    markdown += "| Item | Value |\n"
    markdown += "|---|---|\n"

    markdown = add_row(
        markdown,
        "Date Taken",
        datetime_original
    )

    markdown = add_row(
        markdown,
        "Date Digitized",
        datetime_digitized
    )

    markdown = add_row(
        markdown,
        "Date Modified",
        datetime_general
    )


    # Image

    markdown += "\n## Image\n\n"
    markdown += "| Item | Value |\n"
    markdown += "|---|---|\n"

    markdown = add_row(
        markdown,
        "File Name",
        file.filename
    )

    markdown = add_row(
        markdown,
        "Format",
        image.format
    )

    markdown = add_row(
        markdown,
        "Width",
        f"{image.width} px"
    )

    markdown = add_row(
        markdown,
        "Height",
        f"{image.height} px"
    )

    markdown = add_row(
        markdown,
        "Color Mode",
        image.mode
    )

    markdown = add_row(
        markdown,
        "File Size",
        f"{len(image_data)} bytes"
    )


    # GPS

    markdown += "\n## GPS\n\n"
    markdown += "| Item | Value |\n"
    markdown += "|---|---|\n"

    markdown = add_row(
        markdown,
        "Latitude",
        latitude
    )

    markdown = add_row(
        markdown,
        "Longitude",
        longitude
    )

    markdown = add_row(
        markdown,
        "Altitude",
        altitude
    )


    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8"
    )
