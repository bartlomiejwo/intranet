from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from apscheduler.triggers.interval import IntervalTrigger


jobs_scheduler = BackgroundScheduler()
jobs_scheduler.start()


def start_job(job_function, job_id, schedule_settings):
    if not jobs_scheduler.get_job(job_id) and schedule_settings.enabled:
        trigger = IntervalTrigger(
                    weeks=schedule_settings.weeks,
                    days=schedule_settings.days,
                    hours=schedule_settings.hours,
                    minutes=schedule_settings.minutes
                )

        if schedule_settings.next_run_time:
            if schedule_settings.next_run_time <= timezone.now():
                now = timezone.now()
                next_run_time = schedule_settings.next_run_time.replace(
                        year=now.year,
                        month=now.month,
                        day=now.day) + timedelta(
                    weeks=schedule_settings.weeks,
                    days=schedule_settings.days,
                    hours=schedule_settings.hours,
                    minutes=schedule_settings.minutes
                )

                jobs_scheduler.add_job(
                    job_function,
                    id=job_id,
                    trigger=trigger,
                    next_run_time=next_run_time
                )
            else:
                jobs_scheduler.add_job(
                    job_function,
                    id=job_id,
                    trigger=trigger,
                    next_run_time=schedule_settings.next_run_time,
                )
        else:
            jobs_scheduler.add_job(
                job_function,
                id=job_id,
                trigger=trigger
            )


def reschedule_job(job_function, job_id, schedule_settings):
    if jobs_scheduler.get_job(job_id):
        jobs_scheduler.remove_job(job_id)
        start_job(job_function, job_id, schedule_settings)
    else:
        start_job(job_function, job_id, schedule_settings)
