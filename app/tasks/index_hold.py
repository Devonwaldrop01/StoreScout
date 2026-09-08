"""Suppress index publication and acknowledge held deliveries without retries."""
from celery import Task
from celery.beat import PersistentScheduler
from app.core.index_hold import index_writes_held, require_index_writes, IndexDeploymentHeld


class IndexTask(Task):
    abstract = True

    def __call__(self, *args, **kwargs):
        try:
            require_index_writes()
            return super().__call__(*args, **kwargs)
        except IndexDeploymentHeld:
            return {"status": "deployment_hold", "note": "no further index work permitted"}

    def apply_async(self, *args, **kwargs):
        require_index_writes()
        return super().apply_async(*args, **kwargs)

    def retry(self, *args, **kwargs):
        require_index_writes()
        return super().retry(*args, **kwargs)


class HeldIndexScheduler(PersistentScheduler):
    def apply_async(self, entry, producer=None, advance=True, **kwargs):
        if entry.task.startswith("app.tasks.store_index.") and index_writes_held():
            # Advance due entries normally, without publishing/backlogging them.
            if advance:
                self.reserve(entry)
            return None
        return super().apply_async(entry, producer=producer, advance=advance, **kwargs)
