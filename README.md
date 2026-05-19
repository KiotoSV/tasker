# Планнер

Простой десктопный планнер задач на Python + Tkinter.
Задачи хранятся как `.txt` файлы в подпапке `tasks/` — никакой БД, никакого бэкенда.

## Установка (Windows)

1. Установить Python 3.10+ с [python.org](https://www.python.org/downloads/).
   **Важно:** при установке поставь галочку **«Add Python to PATH»**.
2. Распаковать (или склонировать) папку с этим проектом — например, в `C:\Users\<имя>\Documents\tasker`.
3. Двойной клик по `install.bat`.
4. На рабочем столе появится ярлык **«Планнер»** с иконкой — запускай.

Всё. `tasks/` создастся автоматически при первом запуске.

## Что делает `install.bat`

Вызывает `install.ps1`, который:
- находит `pythonw.exe` в системе,
- устанавливает пакет в editable-режиме (`pip install -e .[dnd]`),
- создаёт на рабочем столе ярлык `Планнер.lnk`,
- прописывает в нём запуск `pythonw -m tasker`, рабочую папку и иконку.

Если что-то пойдёт не так — окно `install.bat` останется открытым, ошибка будет видна.

## Запуск без ярлыка

```
python -m tasker
```

(из любой папки — пакет установлен в editable-режиме, путь к `tasks/` определяется относительно корня проекта.)

## Формат файла задачи

```
status: pending
project: C:\dev\my-project
created: 2026-05-18 11:44
completed:

Произвольное описание задачи.
Может быть многострочным.
```

- `status` — `pending` или `done`.
- `project` — путь к папке (или произвольная строка). Можно несколько строк `project:` подряд.
- Имя файла = заголовок задачи.

## Структура проекта

```
tasker/
├── pyproject.toml          # описание пакета и зависимости
├── icon.ico                # иконка приложения
├── install.bat / .ps1      # установка для Windows
├── make_icon.py            # регенерация иконки
├── tasks/                  # пользовательские данные (gitignored)
├── tests/                  # pytest + smoke UI
└── src/
    └── tasker/
        ├── __main__.py     # python -m tasker
        ├── app.py          # main()
        ├── config.py       # пути и форматы
        ├── platform_utils.py
        ├── tasks.py        # TaskRepository + парсинг/запись .txt
        ├── attachments.py  # папки вложений, DnD-пути
        └── ui/
            ├── theme.py    # ttk-стили
            ├── widgets.py  # Toast, FilterBar, SearchBox, шорткаты
            ├── task_list.py
            ├── editor.py
            ├── main_window.py
            └── dnd.py      # обёртка над tkinterdnd2
```

## Тесты

```
pip install -e .[dev]
pytest
```

## Регенерация иконки

`icon.ico` уже лежит в репозитории. Если хочешь её перерисовать:

```
pip install pillow
python make_icon.py
```
