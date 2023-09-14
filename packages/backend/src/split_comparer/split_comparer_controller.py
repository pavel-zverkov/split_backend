from random import randint
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


split_comparer_router = APIRouter()
template_list = Jinja2Templates(directory='src/html')


@split_comparer_router.get(
    "/split_compare/",
    tags=['split'],
    response_class=HTMLResponse
)
async def compare_split(request: Request):
    competitor_1 = 'Хамурзова Мария'
    competitor_2 = 'Хамурзов Владимир'
    data = [
        ['1 (34)', '00:15', '00:16', '-00:01'],
        ['2 (32)', '01:15', '01:10', '+00:05'],
        ['3 (35)', '00:16', '00:16', '=']
    ]
    render = template_list.TemplateResponse(
        'split.html',
        {
            'request': {'extensions': '.exe'},
            'competitor_1': competitor_1,
            'competitor_2': competitor_2,
            'data': data
        }
    )

    return render
#     return """
# <!DOCTYPE html>
# <html>
#   <head>
#     <title>Таблица</title>
#     <link rel="stylesheet" type="text/css" href="/css/split_compare_style.css">
#   </head>
#   <body>
#     <table>
#       <tr>
#         <th></th>
#         <th>Хамурзова Мария</th>
#         <th>Хамурзов Владимир</th>
#         <th></th>
#       </tr>
#       <tr>
#         <td>1 (39)</td>
#         <td>01:43</td>
#         <td>03:01</td>
#         <td>+ 02:14</td>
#       </tr>
#       <tr>
#         <td>1 (39)</td>
#         <td>02:14</td>
#         <td>01:17</td>
#         <td>- 02:14</td>
#       </tr>
#       <tr>
#         <td>1 (39)</td>
#         <td>02:14</td>
#         <td>02:14</td>
#         <td>=</td>
#       </tr>
#     </table>

#     <script src="/java_script/split_compare.js"></script>
#   </body>
# </html>
#     """
