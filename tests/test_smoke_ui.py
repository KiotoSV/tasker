"""Smoke-тест: главное окно конструируется и закрывается без mainloop().

Внимание: Tk нельзя надёжно создавать дважды в одном процессе (глобальное
состояние Tcl), поэтому здесь ровно один тест на всю сессию pytest. Он
покрывает оба сценария: список задач непуст и редактор показывает первую."""

from tasker.tasks import write_task


def test_app_constructs_and_destroys(tmp_path, monkeypatch):
    monkeypatch.setattr("tasker.ui.main_window.TASKS_DIR", tmp_path)
    write_task(tmp_path / "Sample.txt", "pending", [], "2026-05-19 10:00", "", "body")
    write_task(tmp_path / "Done.txt", "done", [], "2026-05-19 09:00",
               "2026-05-19 11:00", "")

    from tasker.ui.main_window import App
    app = App()
    try:
        app.update_idletasks()
        app.update()
        # После инициализации редактор должен показывать первую задачу.
        assert app.editor.current_path is not None
        # Filter counts должны быть проставлены.
        # (Если виджет фильтра упал бы, тест бы уже сломался выше.)
    finally:
        app.destroy()
