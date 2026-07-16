from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.job import JobStatus,Job
from app.models.workflow import (
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepStatus,
)
from app.schemas.job import JobCreateRequest
from app.schemas.workflow import (
    CsvCleaningWorkflowCreateRequest,
    WorkflowCreateRequest,
)
from app.services.file_service import get_file_by_id
from app.services.job_service import create_job
from app.models.file import File
from datetime import datetime, timezone

async def create_workflow(
    db: AsyncSession,
    workflow_create: WorkflowCreateRequest,
) -> Workflow:
    workflow = Workflow(
        name=workflow_create.name,
        input_file_id=workflow_create.input_file_id,
        config=workflow_create.config,
        status=WorkflowStatus.CREATED,
    )

    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)

    return workflow


async def list_workflows(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Workflow]:
    result = await db.execute(
        select(Workflow)
        .order_by(Workflow.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(result.scalars().all())


async def get_workflow_by_id(
    db: AsyncSession,
    workflow_id: int,
) -> Workflow | None:
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(Workflow.id == workflow_id)
    )

    return result.scalar_one_or_none()


async def add_workflow_step(
    db: AsyncSession,
    *,
    workflow_id: int,
    step_name: str,
    step_order: int,
    job_id: int | None = None,
) -> WorkflowStep:
    step = WorkflowStep(
        workflow_id=workflow_id,
        step_name=step_name,
        step_order=step_order,
        job_id=job_id,
    )

    db.add(step)
    await db.commit()
    await db.refresh(step)

    return step


async def start_csv_cleaning_workflow(
    db: AsyncSession,
    request: CsvCleaningWorkflowCreateRequest,
) -> dict[str, object]:
    input_file = await get_file_by_id(db, request.input_file_id)

    if input_file is None:
        raise ValueError("Input file not found")

    if not input_file.storage_path.lower().endswith(".csv"):
        raise ValueError("CSV cleaning workflow requires a .csv file")

    workflow = Workflow(
        name="csv_cleaning_pipeline",
        input_file_id=request.input_file_id,
        status=WorkflowStatus.RUNNING,
        config={
        "clean_options": request.clean_options,
        },
    )

    db.add(workflow)
    await db.flush()
    await db.refresh(workflow)

    first_job = await create_job(
    db=db,
    task_type="csv_profile",
    payload={
        "file_id": request.input_file_id,
    },
    max_retries=3,
    )

    first_step = WorkflowStep(
        workflow_id=workflow.id,
        job_id=first_job.id,
        step_name="profile_input",
        step_order=1,
        status=WorkflowStepStatus.QUEUED,
    )

    db.add(first_step)
    await db.commit()
    await db.refresh(workflow)
    await db.refresh(first_step)

    return {
        "workflow_id": workflow.id,
        "workflow_status": workflow.status,
        "first_step_id": first_step.id,
        "first_job_id": first_job.id,
        "message": "CSV cleaning workflow started",
    }


async def update_workflow_step_status_for_job(
    db: AsyncSession,
    *,
    job_id: int,
    job_status: JobStatus,
) -> None:
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.job_id == job_id)
    )
    workflow_step = result.scalar_one_or_none()

    if workflow_step is None:
        return

    if job_status == JobStatus.RUNNING:
        workflow_step.status = WorkflowStepStatus.RUNNING
    elif job_status == JobStatus.SUCCESS:
        workflow_step.status = WorkflowStepStatus.SUCCESS
    elif job_status == JobStatus.FAILED:
        workflow_step.status = WorkflowStepStatus.FAILED
    else:
        return

    await db.flush()


# async def create_next_step_after_success(
#     db: AsyncSession,
#     *,
#     completed_job_id: int,
# ) -> None:
#     result = await db.execute(
#         select(WorkflowStep)
#         .options(selectinload(WorkflowStep.workflow))
#         .where(WorkflowStep.job_id == completed_job_id)
#     )

#     completed_step = result.scalar_one_or_none()

#     if completed_step is None:
#         return

#     workflow = completed_step.workflow

#     if workflow.name != "csv_cleaning_pipeline":
#         return

#     if completed_step.step_name != "profile_input":
#         return

#     existing_result = await db.execute(
#         select(WorkflowStep).where(
#             WorkflowStep.workflow_id == workflow.id,
#             WorkflowStep.step_name == "clean_csv",
#         )
#     )
#     existing_step = existing_result.scalar_one_or_none()

#     if existing_step is not None:
#         return

#     clean_options = {}

#     if workflow.config and isinstance(workflow.config, dict):
#         clean_options = workflow.config.get("clean_options", {}) or {}

#     clean_job = await create_job(
#         db=db,
#         task_type="csv_clean_basic",
#         payload={
#             "file_id": workflow.input_file_id,
#             "clean_options": clean_options,
#         },
#         max_retries=3,
#     )

#     clean_step = WorkflowStep(
#         workflow_id=workflow.id,
#         job_id=clean_job.id,
#         step_name="clean_csv",
#         step_order=2,
#         status=WorkflowStepStatus.QUEUED,
#     )

#     db.add(clean_step)
#     await db.commit()


async def create_next_step_after_success(
    db: AsyncSession,
    *,
    completed_job_id: int,
) -> None:
    result = await db.execute(
        select(WorkflowStep)
        .options(selectinload(WorkflowStep.workflow))
        .where(WorkflowStep.job_id == completed_job_id)
    )

    completed_step = result.scalar_one_or_none()

    if completed_step is None:
        return

    workflow = completed_step.workflow

    if workflow.name != "csv_cleaning_pipeline":
        return

    if completed_step.step_name == "profile_input":
        existing_result = await db.execute(
            select(WorkflowStep).where(
                WorkflowStep.workflow_id == workflow.id,
                WorkflowStep.step_name == "clean_csv",
            )
        )
        existing_step = existing_result.scalar_one_or_none()

        if existing_step is not None:
            return

        clean_options = {}

        if workflow.config and isinstance(workflow.config, dict):
            clean_options = workflow.config.get("clean_options", {}) or {}

        clean_job = await create_job(
            db=db,
            task_type="csv_clean_basic",
            payload={
                "file_id": workflow.input_file_id,
                "clean_options": clean_options,
            },
            max_retries=3,
        )

        clean_step = WorkflowStep(
            workflow_id=workflow.id,
            job_id=clean_job.id,
            step_name="clean_csv",
            step_order=2,
            status=WorkflowStepStatus.QUEUED,
        )

        db.add(clean_step)
        await db.commit()
        return

    if completed_step.step_name == "clean_csv":
        existing_result = await db.execute(
            select(WorkflowStep).where(
                WorkflowStep.workflow_id == workflow.id,
                WorkflowStep.step_name == "profile_output",
            )
        )
        existing_step = existing_result.scalar_one_or_none()

        if existing_step is not None:
            return

        completed_job_result = await db.execute(
            select(Job).where(Job.id == completed_job_id)
        )
        completed_job = completed_job_result.scalar_one_or_none()

        if completed_job is None:
            return

        job_result = completed_job.result or {}

        output_file_id = (
            job_result.get("output_file_id")
            or job_result.get("cleaned_file_id")
            or job_result.get("file_id")
        )

        if output_file_id is None:
            raise ValueError(
                f"Clean CSV job {completed_job_id} did not return output_file_id"
            )

        profile_output_job = await create_job(
            db=db,
            task_type="csv_profile",
            payload={
                "file_id": output_file_id,
            },
            max_retries=3,
        )

        profile_output_step = WorkflowStep(
            workflow_id=workflow.id,
            job_id=profile_output_job.id,
            step_name="profile_output",
            step_order=3,
            status=WorkflowStepStatus.QUEUED,
        )

        db.add(profile_output_step)
        await db.commit()
        return


# async def get_csv_cleaning_workflow_result(
#     db: AsyncSession,
#     *,
#     workflow_id: int,
# ) -> dict[str, object] | None:
#     result = await db.execute(
#         select(Workflow)
#         .options(selectinload(Workflow.steps))
#         .where(Workflow.id == workflow_id)
#     )
#     workflow = result.scalar_one_or_none()

#     if workflow is None:
#         return None

#     if workflow.name != "csv_cleaning_pipeline":
#         raise ValueError("Workflow is not a CSV cleaning workflow")

#     job_ids = [
#         step.job_id
#         for step in workflow.steps
#         if step.job_id is not None
#     ]

#     jobs_by_id = {}

#     if job_ids:
#         jobs_result = await db.execute(
#             select(Job).where(Job.id.in_(job_ids))
#         )
#         jobs = jobs_result.scalars().all()
#         jobs_by_id = {
#             job.id: job
#             for job in jobs
#         }

#     steps = sorted(
#         workflow.steps,
#         key=lambda step: step.step_order,
#     )

#     input_profile = None
#     cleaning_result = None
#     output_profile = None
#     cleaned_file_id = None

#     step_responses = []

#     for step in steps:
#         job = jobs_by_id.get(step.job_id) if step.job_id is not None else None
#         job_result = job.result if job is not None else None

#         if step.step_name == "profile_input":
#             input_profile = job_result

#         elif step.step_name == "clean_csv":
#             cleaning_result = job_result

#             if isinstance(job_result, dict):
#                 cleaned_file_id = (
#                     job_result.get("output_file_id")
#                     or job_result.get("cleaned_file_id")
#                     or job_result.get("file_id")
#                 )

#         elif step.step_name == "profile_output":
#             output_profile = job_result

#         step_responses.append(
#             {
#                 "step_name": step.step_name,
#                 "step_order": step.step_order,
#                 "status": step.status,
#                 "job_id": step.job_id,
#                 "job_status": job.status.value if job is not None else None,
#             }
#         )

#     return {
#         "workflow_id": workflow.id,
#         "workflow_status": workflow.status,
#         "input_file_id": workflow.input_file_id,
#         "cleaned_file_id": cleaned_file_id,
#         "input_profile": input_profile,
#         "cleaning_result": cleaning_result,
#         "output_profile": output_profile,
#         "steps": step_responses,
#     }



# async def get_csv_cleaning_workflow_result(
#     db: AsyncSession,
#     *,
#     workflow_id: int,
# ) -> dict[str, object] | None:
#     result = await db.execute(
#         select(Workflow)
#         .options(selectinload(Workflow.steps))
#         .where(Workflow.id == workflow_id)
#     )
#     workflow = result.scalar_one_or_none()

#     if workflow is None:
#         return None

#     if workflow.name != "csv_cleaning_pipeline":
#         raise ValueError("Workflow is not a CSV cleaning workflow")

#     job_ids = [
#         step.job_id
#         for step in workflow.steps
#         if step.job_id is not None
#     ]

#     jobs_by_id = {}

#     if job_ids:
#         jobs_result = await db.execute(
#             select(Job).where(Job.id.in_(job_ids))
#         )
#         jobs = jobs_result.scalars().all()
#         jobs_by_id = {
#             job.id: job
#             for job in jobs
#         }

#     steps = sorted(
#         workflow.steps,
#         key=lambda step: step.step_order,
#     )

#     input_profile = None
#     cleaning_result = None
#     output_profile = None
#     cleaned_file_id = None

#     step_responses = []

#     for step in steps:
#         job = jobs_by_id.get(step.job_id) if step.job_id is not None else None
#         job_result = job.result if job is not None else None

#         if step.step_name == "profile_input":
#             input_profile = job_result

#         elif step.step_name == "clean_csv":
#             cleaning_result = job_result

#             if isinstance(job_result, dict):
#                 cleaned_file_id = (
#                     job_result.get("output_file_id")
#                     or job_result.get("cleaned_file_id")
#                     or job_result.get("file_id")
#                 )

#         elif step.step_name == "profile_output":
#             output_profile = job_result

#             if cleaned_file_id is None and job is not None and isinstance(job.payload, dict):
#                 cleaned_file_id = job.payload.get("file_id")

#         step_responses.append(
#             {
#                 "step_name": step.step_name,
#                 "step_order": step.step_order,
#                 "status": step.status,
#                 "job_id": step.job_id,
#                 "job_status": job.status.value if job is not None else None,
#             }
#         )

#     required_step_names = [
#         "profile_input",
#         "clean_csv",
#         "profile_output",
#     ]

#     steps_by_name = {
#         step.step_name: step
#         for step in steps
#     }

#     steps_completed = sum(
#         1
#         for step_name in required_step_names
#         if (
#             step_name in steps_by_name
#             and steps_by_name[step_name].status == WorkflowStepStatus.SUCCESS
#         )
#     )

#     steps_total = len(required_step_names)
#     progress_percent = int((steps_completed / steps_total) * 100)

#     current_step = None

#     for step_name in required_step_names:
#         step = steps_by_name.get(step_name)

#         if step is None:
#             current_step = step_name
#             break

#         if step.status in {
#             WorkflowStepStatus.QUEUED,
#             WorkflowStepStatus.RUNNING,
#             WorkflowStepStatus.FAILED,
#         }:
#             current_step = step_name
#             break

#     if steps_completed == steps_total:
#         current_step = "completed"

#         cleaned_file = None

#         if cleaned_file_id is not None:
#             file_result = await db.execute(
#                 select(File).where(File.id == cleaned_file_id)
#             )
#             cleaned_file_model = file_result.scalar_one_or_none()

#             if cleaned_file_model is not None:
#                 cleaned_file = {
#                     "id": cleaned_file_model.id,
#                     "original_filename": getattr(cleaned_file_model, "original_filename", None),
#                     "storage_path": getattr(cleaned_file_model, "storage_path", None),
#                     "content_type": getattr(cleaned_file_model, "content_type", None),
#                     "size_bytes": getattr(cleaned_file_model, "size_bytes", None),
#                     "download_url": f"/files/{cleaned_file_model.id}/download",

#                 }

#         return {
#             "workflow_id": workflow.id,
#             "workflow_status": workflow.status,
#             "input_file_id": workflow.input_file_id,
#             "cleaned_file_id": cleaned_file_id,
#             "cleaned_file": cleaned_file,
#             "input_profile": input_profile,
#             "cleaning_result": cleaning_result,
#             "output_profile": output_profile,
#             "steps": step_responses,
#             "progress": {
#                 "steps_total": steps_total,
#                 "steps_completed": steps_completed,
#                 "progress_percent": progress_percent,
#                 "current_step": current_step
#             },
#             "failure": failure,
#         }


async def get_csv_cleaning_workflow_result(
    db: AsyncSession,
    *,
    workflow_id: int,
) -> dict[str, object] | None:
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if workflow is None:
        return None

    if workflow.name != "csv_cleaning_pipeline":
        raise ValueError("Workflow is not a CSV cleaning workflow")

    job_ids = [
        step.job_id
        for step in workflow.steps
        if step.job_id is not None
    ]

    jobs_by_id = {}

    if job_ids:
        jobs_result = await db.execute(
            select(Job).where(Job.id.in_(job_ids))
        )
        jobs = jobs_result.scalars().all()
        jobs_by_id = {
            job.id: job
            for job in jobs
        }

    steps = sorted(
        workflow.steps,
        key=lambda step: step.step_order,
    )

    input_profile = None
    cleaning_result = None
    output_profile = None
    cleaned_file_id = None
    failure = None

    step_responses = []

    for step in steps:
        job = jobs_by_id.get(step.job_id) if step.job_id is not None else None
        job_result = job.result if job is not None else None

        if (
            failure is None
            and step.status == WorkflowStepStatus.FAILED
        ):
            failure = {
                "failed_step": step.step_name,
                "failed_job_id": step.job_id,
                "error_message": job.error_message if job is not None else None,
            }

        if step.step_name == "profile_input":
            input_profile = job_result

        elif step.step_name == "clean_csv":
            cleaning_result = job_result

            if isinstance(job_result, dict):
                cleaned_file_id = (
                    job_result.get("output_file_id")
                    or job_result.get("cleaned_file_id")
                    or job_result.get("file_id")
                )

        elif step.step_name == "profile_output":
            output_profile = job_result

            if (
                cleaned_file_id is None
                and job is not None
                and isinstance(job.payload, dict)
            ):
                cleaned_file_id = job.payload.get("file_id")

        step_responses.append(
            {
                "step_name": step.step_name,
                "step_order": step.step_order,
                "status": step.status,
                "job_id": step.job_id,
                "job_status": job.status.value if job is not None else None,
            }
        )

    required_step_names = [
        "profile_input",
        "clean_csv",
        "profile_output",
    ]

    steps_by_name = {
        step.step_name: step
        for step in steps
    }

    steps_completed = sum(
        1
        for step_name in required_step_names
        if (
            step_name in steps_by_name
            and steps_by_name[step_name].status == WorkflowStepStatus.SUCCESS
        )
    )

    steps_total = len(required_step_names)
    progress_percent = int((steps_completed / steps_total) * 100)

    current_step = None

    for step_name in required_step_names:
        step = steps_by_name.get(step_name)

        if step is None:
            current_step = step_name
            break

        if step.status in {
            WorkflowStepStatus.QUEUED,
            WorkflowStepStatus.RUNNING,
            WorkflowStepStatus.FAILED,
        }:
            current_step = step_name
            break

    if steps_completed == steps_total:
        current_step = "completed"

    cleaned_file = None

    if cleaned_file_id is not None:
        file_result = await db.execute(
            select(File).where(File.id == cleaned_file_id)
        )
        cleaned_file_model = file_result.scalar_one_or_none()

        if cleaned_file_model is not None:
            cleaned_file = {
                "id": cleaned_file_model.id,
                "original_filename": getattr(cleaned_file_model, "original_filename", None),
                "storage_path": getattr(cleaned_file_model, "storage_path", None),
                "content_type": getattr(cleaned_file_model, "content_type", None),
                "size_bytes": getattr(cleaned_file_model, "size_bytes", None),
                "download_url": f"/files/{cleaned_file_model.id}/download",
            }

    return {
        "workflow_id": workflow.id,
        "workflow_status": workflow.status,
        "input_file_id": workflow.input_file_id,
        "cleaned_file_id": cleaned_file_id,
        "cleaned_file": cleaned_file,
        "input_profile": input_profile,
        "cleaning_result": cleaning_result,
        "output_profile": output_profile,
        "steps": step_responses,
        "progress": {
            "steps_total": steps_total,
            "steps_completed": steps_completed,
            "progress_percent": progress_percent,
            "current_step": current_step,
        },
        "failure": failure,
    }




async def refresh_csv_workflow_status(db: AsyncSession, workflow_id: int) -> None:
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if workflow is None or workflow.name != "csv_cleaning_pipeline":
        return

    steps_result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id)
    )
    steps = list(steps_result.scalars().all())
    if not steps:
        return

    required = {"profile_input", "clean_csv", "profile_output"}
    by_name = {s.step_name: s for s in steps}

    # If any required step failed => workflow failed
    for name in required:
        step = by_name.get(name)
        if step is not None and step.status == WorkflowStepStatus.FAILED:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now(timezone.utc)
            await db.flush()
            return

    # If all required steps exist and are success => workflow success
    all_done = all(
        (name in by_name and by_name[name].status == WorkflowStepStatus.SUCCESS)
        for name in required
    )
    if all_done:
        workflow.status = WorkflowStatus.SUCCESS
        workflow.completed_at = datetime.now(timezone.utc)
        await db.flush()
        return

    # Otherwise still running
    workflow.status = WorkflowStatus.RUNNING
    workflow.completed_at = None
    await db.flush()