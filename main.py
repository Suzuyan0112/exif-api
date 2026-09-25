
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from PIL import Image, ExifTags
from io import BytesIO


app = FastAPI(
    title="EXIF Markdown API",
    description="画像からEXIF情報を取得してMarkdown形式で返すREST API",
    version="1.0.0"
)


def markdown_escape(value):
    if value is None:
        return ""

    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def format_exif_value(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)

    return str(value)


def add_exif_rows(rows, exif_data, section="EXIF"):
    for tag_id, value in exif_data.items():

        tag_name = ExifTags.TAGS.get(
            tag_id,
            str(tag_id)
        )

        rows.append(
            (
                section,
                str(tag_name),
                markdown_escape(
                    format_exif_value(value)
                )
            )
        )


@app.get("/", response_class=PlainTextResponse)
async def root():

    markdown = (
        "# EXIF Markdown REST API\n\n"
        "画像をPOSTするとEXIF情報をMarkdown形式で返します。\n\n"
        "## Endpoint\n\n"
        "`POST /exif`\n\n"
        "## Swagger UI\n\n"
        "`GET /docs`\n\n"
        "## Health Check\n\n"
        "`GET /health`\n"
    )

    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown; charset=utf-8"
    )


@app.get("/health")
async def health():

    return {
        "status": "ok"
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

        if len(image_data) == 0:
            raise ValueError(
                "ファイルが空です"
            )

        image = Image.open(
            BytesIO(image_data)
        )

        image.verify()

        image = Image.open(
            BytesIO(image_data)
        )

        exif = image.getexif()

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"画像を読み込めませんでした: {e}"
        )


    markdown = "# EXIF Information\n\n"


    markdown += "## Image\n\n"

    markdown += "| Item | Value |\n"
    markdown += "|---|---|\n"

    markdown += (
        f"| File Name | "
        f"`{markdown_escape(file.filename)}` |\n"
    )

    markdown += (
        f"| Content Type | "
        f"`{markdown_escape(file.content_type)}` |\n"
    )

    markdown += (
        f"| Format | "
        f"`{markdown_escape(image.format)}` |\n"
    )

    markdown += (
        f"| Width | "
        f"{image.width} px |\n"
    )

    markdown += (
        f"| Height | "
        f"{image.height} px |\n"
    )

    markdown += (
        f"| Mode | "
        f"`{markdown_escape(image.mode)}` |\n"
    )

    markdown += (
        f"| File Size | "
        f"{len(image_data)} bytes |\n"
    )


    markdown += "\n## EXIF\n\n"


    if not exif:

        markdown += (
            "EXIF情報はありません。\n"
        )

    else:

        rows = []

        add_exif_rows(
            rows,
            exif,
            "Main"
        )


        try:
            if hasattr(ExifTags, "IFD"):

                exif_ifd = exif.get_ifd(
                    ExifTags.IFD.Exif
                )

                if exif_ifd:
                    add_exif_rows(
                        rows,
                        exif_ifd,
                        "Exif"
                    )

        except Exception:
            pass


        try:
            if hasattr(ExifTags, "IFD"):

                gps_ifd = exif.get_ifd(
                    ExifTags.IFD.GPSInfo
                )

                if gps_ifd:

                    for tag_id, value in gps_ifd.items():

                        tag_name = (
                            ExifTags.GPSTAGS.get(
                                tag_id,
                                str(tag_id)
                            )
                        )

                        rows.append(
                            (
                                "GPS",
                                str(tag_name),
                                markdown_escape(
                                    format_exif_value(
                                        value
                                    )
                                )
                            )
                        )

        except Exception:
            pass


        markdown += (
            "| Section | Tag | Value |\n"
        )

        markdown += (
            "|---|---|---|\n"
        )


        rows.sort(
            key=lambda x: (
                x[0],
                x[1]
            )
        )


        for section, tag_name, value in rows:

            markdown += (
                f"| `{section}` "
                f"| `{tag_name}` "
                f"| {value} |\n"
            )


    return PlainTextResponse(
        content=markdown,
        media_type=(
            "text/markdown; charset=utf-8"
        )
    )
