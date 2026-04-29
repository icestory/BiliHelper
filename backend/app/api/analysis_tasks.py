from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.analysis import AnalysisTaskCreate, AnalysisTaskResponse, PartAnalysisDetail
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api", tags=["分析任务"])


@router.post("/analysis-tasks", response_model=AnalysisTaskResponse, status_code=201)
def create_analysis_task(
    body: AnalysisTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建视频分析任务（异步执行）"""
    return AnalysisService(db).create_task(current_user.id, body)


@router.get("/analysis-tasks/{task_id}", response_model=AnalysisTaskResponse)
def get_analysis_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询任务状态（前端轮询此接口）"""
    return AnalysisService(db).get_task(task_id, current_user.id)


@router.get("/parts/{part_id}/analysis", response_model=PartAnalysisDetail)
def get_part_analysis(
    part_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取单个分 P 的分析详情（文案、总结、章节）"""
    return AnalysisService(db).get_part_analysis(part_id)
