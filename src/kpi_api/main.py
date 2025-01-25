"""
Ce module contient les routes de l'API FastAPI.
"""

from fastapi import FastAPI, HTTPException, Query

import kpi_api.routes.gitlab as gitlab
import kpi_api.routes.kimai as kimai
import kpi_api.routes.nextcloud as nextcloud
from kpi_api.routes.screenshot import screenshot_issue_board

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Metrics API for GitLab and Kimai"}


@app.get("/metrics/time_spent")
async def time_spent(
        group_path: str = Query(..., description="Path du groupe GitLab"),
        created_after: str = Query(..., description="Date ISO pour filtrer les issues")
):
    try:
        data = await gitlab.fetch_time_spent_by_user(group_path, created_after)
        return {"time_by_user": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/opened_closed_issues")
async def opened_closed_issues(
        group_path: str = Query(..., description="Path du groupe GitLab"),
        created_after: str = Query(..., description="Date ISO pour filtrer les issues"),
        created_before: str = Query(..., description="Date ISO pour filtrer les issues")
):
    try:
        data = await gitlab.fetch_opened_closed_tasks(group_path, created_after, created_before)
        return {"opened_closed_tasks": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/burndown")
async def burndown(
        group_path: str = Query(..., description="Path du groupe GitLab"),
        created_after: str = Query(..., description="Date ISO pour filtrer les issues"),
        created_before: str = Query(..., description="Date ISO pour filtrer les issues")
):
    try:
        data = await gitlab.burndown_chart(group_path, created_after, created_before)
        return {"burndown": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/resolve_time")
async def resolve_time(
        group_path: str = Query(..., description="Path du groupe GitLab"),
        created_after: str = Query(..., description="Date ISO pour filtrer les issues"),
        created_before: str = Query(..., description="Date ISO pour filtrer les issues")
):
    try:
        data = await gitlab.resolve_time(group_path, created_after, created_before)
        return {"resolve_time": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/time_per_wp")
async def time_per_wp(
        group_path: str = Query(..., description="Path du groupe GitLab"),
        created_after: str = Query(..., description="Date ISO pour filtrer les issues"),
):
    try:
        data = await gitlab.temps_passe_par_wp(group_path, created_after)
        return {"time_per_wp": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/resolve_time_mean")
async def resolve_time_mean(
        group_path: str = Query(..., description="Path du groupe GitLab"),
        created_after: str = Query(..., description="Date ISO pour filtrer les issues"),
        created_before: str = Query(..., description="Date ISO pour filtrer les issues")
):
    try:
        data = await gitlab.resolve_time_mean(group_path, created_after, created_before)
        return {"resolve_time_mean": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kimai/hours")
async def kimai_hours(
        created_after: str = Query(..., example="2023-10-01T00:00:00"),
        created_before: str = Query(..., example="2023-10-31T23:59:59")
):
    try:

        clean_from = created_after.replace('Z', '')
        clean_to = created_before.replace('Z', '')
        data = kimai.get_all_users_hours(clean_from, clean_to)
        return {"kimai_hours": data}
    except Exception as e:
        print(f"ERREUR FINALE: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kimai/current_week")
async def kimai_current_week():
    try:
        data = kimai.get_all_current_week_hours()
        return {"kimai_hours": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kiami/last_week")
async def kimai_last_week():
    try:
        data = kimai.get_all_last_week_hours()
        return {"kimai_hours": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/burnup")
async def burnup(
        group_path: str = Query(..., description="Path du groupe GitLab"),
        created_after: str = Query(..., description="Date ISO pour filtrer les issues"),
        created_before: str = Query(..., description="Date ISO pour filtrer les issues")
):
    try:
        data = await gitlab.fetch_burnup_data(group_path, created_after, created_before)
        return {"burnup": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/summary")
async def summary(
        group_path: str = Query(..., description="Path du groupe GitLab"),
        created_after: str = Query(..., description="Date ISO pour filtrer les issues"),
        created_before: str = Query(..., description="Date ISO pour filtrer les issues")

):
    try:
        data = await gitlab.fetch_issues_summary(group_path, created_after, created_before)
        return {"summary": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/issues_count_by_user")
async def issues_count_by_user(
        group_path: str = Query(..., description="Path du groupe GitLab"),
        created_after: str = Query(..., description="Date ISO pour filtrer les issues"),
        created_before: str = Query(..., description="Date ISO pour filtrer les issues")
):
    try:
        data = await gitlab.fetch_open_issues_count_by_user(group_path, created_after, created_before)
        return {"issues_count_by_user": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gitlab/screenshot")
async def get_screenshot():
    """
    Capture un screenshot d'une URL protégée en utilisant un token d'authentification.
    """
    try:
        return await screenshot_issue_board()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la capture du screenshot : {e}")


@app.get("/calendar/full")
async def get_cal():
    try:
        data = nextcloud.get_nextcloud_events()
        return {"cal": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calendar/next_class")
async def get_cal_next_class():
    try:
        return nextcloud.get_next_cours()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calendar/next_pic_event")
async def get_cal_next_pic_event():
    try:
        return nextcloud.get_next_pic_event()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
