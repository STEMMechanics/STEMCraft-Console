from fastapi import Request

from fastapi.templating import (
    Jinja2Templates,
)


templates = Jinja2Templates(
    directory="app/templates"
)


def render_page(
    request: Request,
    full_template: str,
    partial_template: str,
    context: dict,
):

    context["request"] = request

    if request.headers.get(
        "HX-Request"
    ) == "true":

        return templates.TemplateResponse(
            request=request,
            name=partial_template,
            context=context,
        )

    return templates.TemplateResponse(
        request=request,
        name=full_template,
        context=context,
    )