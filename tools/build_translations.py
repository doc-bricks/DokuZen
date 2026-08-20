#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generates comprehensive locales/translations.json for DokuZen."""

import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
locales_dir = root / "locales"
locales_dir.mkdir(parents=True, exist_ok=True)
out_file = locales_dir / "translations.json"

TRANSLATIONS = {
    # Application & General
    "DokuZen": {
        "de": "DokuZen", "en": "DokuZen", "es": "DokuZen", "zh": "DokuZen", "ja": "DokuZen", "ru": "DokuZen"
    },
    "DokuZen Pro": {
        "de": "DokuZen Pro", "en": "DokuZen Pro", "es": "DokuZen Pro", "zh": "DokuZen Pro", "ja": "DokuZen Pro", "ru": "DokuZen Pro"
    },
    "Einstellungen": {
        "de": "Einstellungen", "en": "Settings", "es": "Configuración", "zh": "设置", "ja": "設定", "ru": "Настройки"
    },
    "Allgemein": {
        "de": "Allgemein", "en": "General", "es": "General", "zh": "常规", "ja": "一般", "ru": "Общие"
    },
    "Darstellung": {
        "de": "Darstellung", "en": "Appearance", "es": "Apariencia", "zh": "外观", "ja": "外観", "ru": "Внешний вид"
    },
    "Tastaturkürzel": {
        "de": "Tastaturkürzel", "en": "Shortcuts", "es": "Atajos de teclado", "zh": "快捷键", "ja": "ショートカット", "ru": "Горячие клавиши"
    },
    "Erweitert": {
        "de": "Erweitert", "en": "Advanced", "es": "Avanzado", "zh": "高级", "ja": "詳細", "ru": "Расширенные"
    },
    "OK": {
        "de": "OK", "en": "OK", "es": "Aceptar", "zh": "确定", "ja": "OK", "ru": "ОК"
    },
    "Abbrechen": {
        "de": "Abbrechen", "en": "Cancel", "es": "Cancelar", "zh": "取消", "ja": "キャンセル", "ru": "Отмена"
    },
    "Zurücksetzen": {
        "de": "Zurücksetzen", "en": "Reset", "es": "Restablecer", "zh": "重置", "ja": "リセット", "ru": "Сбросить"
    },
    "Speichern": {
        "de": "Speichern", "en": "Save", "es": "Guardar", "zh": "保存", "ja": "保存", "ru": "Сохранить"
    },
    "Laden": {
        "de": "Laden", "en": "Load", "es": "Cargar", "zh": "加载", "ja": "読み込み", "ru": "Загрузить"
    },
    "Löschen": {
        "de": "Löschen", "en": "Delete", "es": "Eliminar", "zh": "删除", "ja": "削除", "ru": "Удалить"
    },
    "Entfernen": {
        "de": "Entfernen", "en": "Remove", "es": "Quitar", "zh": "移除", "ja": "削除", "ru": "Удалить"
    },
    "Hinzufügen": {
        "de": "Hinzufügen", "en": "Add", "es": "Añadir", "zh": "添加", "ja": "追加", "ru": "Добавить"
    },
    "Aktualisieren": {
        "de": "Aktualisieren", "en": "Refresh", "es": "Actualizar", "zh": "刷新", "ja": "更新", "ru": "Обновить"
    },
    "Suchen": {
        "de": "Suchen", "en": "Search", "es": "Buscar", "zh": "搜索", "ja": "検索", "ru": "Поиск"
    },
    "Filter": {
        "de": "Filter", "en": "Filter", "es": "Filtro", "zh": "过滤器", "ja": "フィルター", "ru": "Фильтр"
    },
    "Filter: Alle": {
        "de": "Filter: Alle", "en": "Filter: All", "es": "Filtro: Todos", "zh": "过滤器: 全部", "ja": "フィルター: すべて", "ru": "Фильтр: Все"
    },
    "Importieren": {
        "de": "Importieren", "en": "Import", "es": "Importar", "zh": "导入", "ja": "インポート", "ru": "Импорт"
    },
    "Exportieren": {
        "de": "Exportieren", "en": "Export", "es": "Exportar", "zh": "导出", "ja": "エクスポート", "ru": "Экспорт"
    },
    "Schließen": {
        "de": "Schließen", "en": "Close", "es": "Cerrar", "zh": "关闭", "ja": "閉じる", "ru": "Закрыть"
    },

    # Menus
    "&Datei": {
        "de": "&Datei", "en": "&File", "es": "&Archivo", "zh": "&文件", "ja": "&ファイル", "ru": "&Файл"
    },
    "&Bearbeiten": {
        "de": "&Bearbeiten", "en": "&Edit", "es": "&Editar", "zh": "&编辑", "ja": "&編集", "ru": "&Правка"
    },
    "&Ansicht": {
        "de": "&Ansicht", "en": "&View", "es": "&Ver", "zh": "&视图", "ja": "&表示", "ru": "&Вид"
    },
    "&Themen": {
        "de": "&Themen", "en": "&Topics", "es": "&Temas", "zh": "&主题", "ja": "&トピック", "ru": "&Темы"
    },
    "&Werkzeuge": {
        "de": "&Werkzeuge", "en": "&Tools", "es": "&Herramientas", "zh": "&工具", "ja": "&ツール", "ru": "&Инструменты"
    },
    "&Hilfe": {
        "de": "&Hilfe", "en": "&Help", "es": "&Ayuda", "zh": "&帮助", "ja": "&ヘルプ", "ru": "&Справка"
    },
    "&Importieren...": {
        "de": "&Importieren...", "en": "&Import...", "es": "&Importar...", "zh": "&导入...", "ja": "&インポート...", "ru": "&Импорт..."
    },
    "Ordner importieren...": {
        "de": "Ordner importieren...", "en": "Import Folder...", "es": "Importar carpeta...", "zh": "导入文件夹...", "ja": "フォルダーをインポート...", "ru": "Импортировать папку..."
    },
    "&Einstellungen...": {
        "de": "&Einstellungen...", "en": "&Settings...", "es": "&Configuración...", "zh": "&设置...", "ja": "&設定...", "ru": "&Настройки..."
    },
    "&Beenden": {
        "de": "&Beenden", "en": "&Exit", "es": "&Salir", "zh": "&退出", "ja": "&終了", "ru": "&Выход"
    },
    "&Neues Thema...": {
        "de": "&Neues Thema...", "en": "&New Topic...", "es": "&Nuevo tema...", "zh": "&新建主题...", "ja": "&新しいトピック...", "ru": "&Новая тема..."
    },
    "&Aktualisieren": {
        "de": "&Aktualisieren", "en": "&Refresh", "es": "&Actualizar", "zh": "&刷新", "ja": "&更新", "ru": "&Обновить"
    },
    "&Suchen...": {
        "de": "&Suchen...", "en": "&Search...", "es": "&Buscar...", "zh": "&搜索...", "ja": "&検索...", "ru": "&Поиск..."
    },

    # Tool Actions & Dialogs
    "&OCR-Texterkennung...": {
        "de": "&OCR-Texterkennung...", "en": "&OCR Text Recognition...", "es": "&Reconocimiento de texto OCR...", "zh": "&OCR文字识别...", "ja": "&OCRテキスト認識...", "ru": "&Распознавание текста (OCR)..."
    },
    "OCR-Texterkennung": {
        "de": "OCR-Texterkennung", "en": "OCR Text Recognition", "es": "Reconocimiento de texto OCR", "zh": "OCR文字识别", "ja": "OCRテキスト認識", "ru": "Распознавание текста (OCR)"
    },
    "PDF &schwärzen...": {
        "de": "PDF &schwärzen...", "en": "&Redact PDF...", "es": "&Censurar PDF...", "zh": "&涂黑PDF...", "ja": "&PDF墨消し...", "ru": "&Редактировать PDF (скрыть)..."
    },
    "PDF Schwärzen": {
        "de": "PDF Schwärzen", "en": "Redact PDF", "es": "Censurar PDF", "zh": "涂黑PDF", "ja": "PDF墨消し", "ru": "Редактирование PDF"
    },
    "Format-&Konvertierung...": {
        "de": "Format-&Konvertierung...", "en": "Format &Conversion...", "es": "&Conversión de formato...", "zh": "格式&转换...", "ja": "形式&変換...", "ru": "&Конвертация формата..."
    },
    "Format-Konvertierung": {
        "de": "Format-Konvertierung", "en": "Format Conversion", "es": "Conversión de formato", "zh": "格式转换", "ja": "形式変換", "ru": "Конвертация формата"
    },
    "PDF-&Marker (M/D/K)...": {
        "de": "PDF-&Marker (M/D/K)...", "en": "PDF &Marker (M/D/K)...", "es": "&Marcador de PDF (M/D/K)...", "zh": "PDF&标记 (M/D/K)...", "ja": "PDF&マーカー (M/D/K)...", "ru": "&Маркер PDF (M/D/K)..."
    },
    "PDF-Marker": {
        "de": "PDF-Marker", "en": "PDF Marker", "es": "Marcador de PDF", "zh": "PDF标记", "ja": "PDFマーカー", "ru": "Маркер PDF"
    },
    "PDFs &zusammenführen...": {
        "de": "PDFs &zusammenführen...", "en": "&Merge PDFs...", "es": "&Combinar PDFs...", "zh": "&合并PDF...", "ja": "&PDF結合...", "ru": "&Объединить PDF..."
    },
    "PDFs zusammenführen": {
        "de": "PDFs zusammenführen", "en": "Merge PDFs", "es": "Combinar PDFs", "zh": "合并PDF", "ja": "PDF結合", "ru": "Объединение PDF"
    },
    "PDF-Seiten &verwalten...": {
        "de": "PDF-Seiten &verwalten...", "en": "&Manage PDF Pages...", "es": "&Gestionar páginas de PDF...", "zh": "&管理PDF页面...", "ja": "&PDFページ管理...", "ru": "&Управление страницами PDF..."
    },
    "PDF-Seiten verwalten": {
        "de": "PDF-Seiten verwalten", "en": "Manage PDF Pages", "es": "Gestionar páginas de PDF", "zh": "管理PDF页面", "ja": "PDFページ管理", "ru": "Управление страницами PDF"
    },
    "PDF-&Annotationen...": {
        "de": "PDF-&Annotationen...", "en": "PDF &Annotations...", "es": "&Anotaciones de PDF...", "zh": "PDF&批注...", "ja": "PDF&注釈...", "ru": "&Аннотации PDF..."
    },
    "PDF-&Werkstatt...": {
        "de": "PDF-&Werkstatt...", "en": "PDF &Workshop...", "es": "&Taller de PDF...", "zh": "PDF&工作坊...", "ja": "PDF&ワークショップ...", "ru": "&Мастерская PDF..."
    },
    "PDF-Werkstatt": {
        "de": "PDF-Werkstatt", "en": "PDF Workshop", "es": "Taller de PDF", "zh": "PDF工作坊", "ja": "PDFワークショップ", "ru": "Мастерская PDF"
    },
    "&Bild-Werkzeuge...": {
        "de": "&Bild-Werkzeuge...", "en": "&Image Tools...", "es": "&Herramientas de imagen...", "zh": "&图像工具...", "ja": "&画像ツール...", "ru": "&Инструменты для изображений..."
    },
    "Bild-Werkzeuge": {
        "de": "Bild-Werkzeuge", "en": "Image Tools", "es": "Herramientas de imagen", "zh": "图像工具", "ja": "画像ツール", "ru": "Инструменты для изображений"
    },
    "&Formular-Builder...": {
        "de": "&Formular-Builder...", "en": "&Form Builder...", "es": "&Constructor de formularios...", "zh": "&表单构建器...", "ja": "&フォームビルダー...", "ru": "&Конструктор форм..."
    },
    "Formular-Builder": {
        "de": "Formular-Builder", "en": "Form Builder", "es": "Constructor de formularios", "zh": "表单构建器", "ja": "フォームビルダー", "ru": "Конструктор форм"
    },
    "&Code-Analyse (.py)...": {
        "de": "&Code-Analyse (.py)...", "en": "&Code Analysis (.py)...", "es": "&Análisis de código (.py)...", "zh": "&代码分析 (.py)...", "ja": "&コード解析 (.py)...", "ru": "&Анализ кода (.py)..."
    },
    "Code-Analyse": {
        "de": "Code-Analyse", "en": "Code Analysis", "es": "Análisis de código", "zh": "代码分析", "ja": "コード解析", "ru": "Анализ кода"
    },
    "PDF-Signatur &einbetten...": {
        "de": "PDF-Signatur &einbetten...", "en": "&Embed PDF Signature...", "es": "&Incrustar firma en PDF...", "zh": "&嵌入PDF签名...", "ja": "&PDF署名を埋め込む...", "ru": "&Встроить подпись в PDF..."
    },
    "Dokument teilen (Split)...": {
        "de": "Dokument teilen (Split)...", "en": "Split Document...", "es": "Dividir documento...", "zh": "拆分文档...", "ja": "ドキュメント分割...", "ru": "Разделить документ..."
    },

    # Panels & Main Window Layout
    "Bibliothek": {
        "de": "Bibliothek", "en": "Library", "es": "Biblioteca", "zh": "文库", "ja": "ライブラリ", "ru": "Библиотека"
    },
    "<b>Bibliothek</b>": {
        "de": "<b>Bibliothek</b>", "en": "<b>Library</b>", "es": "<b>Biblioteca</b>", "zh": "<b>文库</b>", "ja": "<b>ライブラリ</b>", "ru": "<b>Библиотека</b>"
    },
    "Dokumente": {
        "de": "Dokumente", "en": "Documents", "es": "Documentos", "zh": "文档", "ja": "ドキュメント", "ru": "Документы"
    },
    "<b>Dokumente</b>": {
        "de": "<b>Dokumente</b>", "en": "<b>Documents</b>", "es": "<b>Documentos</b>", "zh": "<b>文档</b>", "ja": "<b>ドキュメント</b>", "ru": "<b>Документы</b>"
    },
    "Vorschau": {
        "de": "Vorschau", "en": "Preview", "es": "Vista previa", "zh": "预览", "ja": "プレビュー", "ru": "Предпросмотр"
    },
    "<b>Vorschau</b>": {
        "de": "<b>Vorschau</b>", "en": "<b>Preview</b>", "es": "<b>Vista previa</b>", "zh": "<b>预览</b>", "ja": "<b>プレビュー</b>", "ru": "<b>Предпросмотр</b>"
    },
    "0 Dokumente": {
        "de": "0 Dokumente", "en": "0 Documents", "es": "0 Documentos", "zh": "0 个文档", "ja": "0 件のドキュメント", "ru": "0 документов"
    },
    "Dokumente: 0": {
        "de": "Dokumente: 0", "en": "Documents: 0", "es": "Documentos: 0", "zh": "文档: 0", "ja": "ドキュメント: 0", "ru": "Документов: 0"
    },
    "0 Ergebnisse": {
        "de": "0 Ergebnisse", "en": "0 Results", "es": "0 Resultados", "zh": "0 个结果", "ja": "0 件の結果", "ru": "0 результатов"
    },
    "Kein Dokument ausgewählt": {
        "de": "Kein Dokument ausgewählt", "en": "No document selected", "es": "Ningún documento seleccionado", "zh": "未选择文档", "ja": "ドキュメントが選択されていません", "ru": "Документ не выбран"
    },
    "Keine Datei geladen": {
        "de": "Keine Datei geladen", "en": "No file loaded", "es": "Ningún archivo cargado", "zh": "未加载文件", "ja": "ファイルが読み込まれていません", "ru": "Файл не загружен"
    },
    "Keine PDF geladen": {
        "de": "Keine PDF geladen", "en": "No PDF loaded", "es": "Ningún PDF cargado", "zh": "未加载PDF", "ja": "PDFが読み込まれていません", "ru": "PDF не загружен"
    },
    "Keine Auswahl": {
        "de": "Keine Auswahl", "en": "No selection", "es": "Sin selección", "zh": "无选择", "ja": "選択なし", "ru": "Нет выбора"
    },

    # Settings Tab Details
    "Pfade": {
        "de": "Pfade", "en": "Paths", "es": "Rutas", "zh": "路径", "ja": "パス", "ru": "Пути"
    },
    "Bibliothek:": {
        "de": "Bibliothek:", "en": "Library:", "es": "Biblioteca:", "zh": "文库:", "ja": "ライブラリ:", "ru": "Библиотека:"
    },
    "Export-Standard:": {
        "de": "Export-Standard:", "en": "Default Export:", "es": "Exportación predeterminada:", "zh": "默认导出:", "ja": "標準エクスポート:", "ru": "Экспорт по умолчанию:"
    },
    "Spawner-Ordner:": {
        "de": "Spawner-Ordner:", "en": "Spawner Folder:", "es": "Carpeta del spawner:", "zh": "生成器文件夹:", "ja": "スポナーフォルダー:", "ru": "Папка спавнера:"
    },
    "Sprache": {
        "de": "Sprache", "en": "Language", "es": "Idioma", "zh": "语言", "ja": "言語", "ru": "Язык"
    },
    "Sprache:": {
        "de": "Sprache:", "en": "Language:", "es": "Idioma:", "zh": "语言:", "ja": "言語:", "ru": "Язык:"
    },
    "Verhalten": {
        "de": "Verhalten", "en": "Behavior", "es": "Comportamiento", "zh": "行为", "ja": "動作", "ru": "Поведение"
    },
    "Automatisch speichern": {
        "de": "Automatisch speichern", "en": "Auto save", "es": "Guardar automáticamente", "zh": "自动保存", "ja": "自動保存", "ru": "Автосохранение"
    },
    "Vor Löschen bestätigen": {
        "de": "Vor Löschen bestätigen", "en": "Confirm before deletion", "es": "Confirmar antes de eliminar", "zh": "删除前确认", "ja": "削除前に確認", "ru": "Подтверждать перед удалением"
    },
    "Fensterposition merken": {
        "de": "Fensterposition merken", "en": "Remember window position", "es": "Recordar posición de ventana", "zh": "记住窗口位置", "ja": "ウィンドウ位置を記憶", "ru": "Запоминать положение окна"
    },
    "Minimiert starten": {
        "de": "Minimiert starten", "en": "Start minimized", "es": "Iniciar minimizado", "zh": "启动时最小化", "ja": "最小化で起動", "ru": "Запускать свернутым"
    },
    "Design": {
        "de": "Design", "en": "Theme", "es": "Tema", "zh": "主题", "ja": "テーマ", "ru": "Тема"
    },
    "Theme:": {
        "de": "Theme:", "en": "Theme:", "es": "Tema:", "zh": "主题:", "ja": "テーマ:", "ru": "Тема:"
    },
    "Hell": {
        "de": "Hell", "en": "Light", "es": "Claro", "zh": "明亮", "ja": "ライト", "ru": "Светлая"
    },
    "Dunkel": {
        "de": "Dunkel", "en": "Dark", "es": "Oscuro", "zh": "暗黑", "ja": "ダーク", "ru": "Темная"
    },
    "Sepia": {
        "de": "Sepia", "en": "Sepia", "es": "Sepia", "zh": "复古", "ja": "セピア", "ru": "Сепия"
    },
    "Nord": {
        "de": "Nord", "en": "Nord", "es": "Nord", "zh": "北欧", "ja": "ノード", "ru": "Север"
    },
    "Ozean": {
        "de": "Ozean", "en": "Ocean", "es": "Océano", "zh": "海洋", "ja": "オーシャン", "ru": "Океан"
    },
    "Schriftgröße:": {
        "de": "Schriftgröße:", "en": "Font Size:", "es": "Tamaño de fuente:", "zh": "字体大小:", "ja": "フォントサイズ:", "ru": "Размер шрифта:"
    },
    "Schriftart:": {
        "de": "Schriftart:", "en": "Font Family:", "es": "Fuente:", "zh": "字体:", "ja": "フォント:", "ru": "Шрифт:"
    },
    "Icon-Größe:": {
        "de": "Icon-Größe:", "en": "Icon Size:", "es": "Tamaño de icono:", "zh": "图标大小:", "ja": "アイコンサイズ:", "ru": "Размер значков:"
    },
    "PDF-Einstellungen": {
        "de": "PDF-Einstellungen", "en": "PDF Settings", "es": "Configuración de PDF", "zh": "PDF设置", "ja": "PDF設定", "ru": "Настройки PDF"
    },
    "PDF-Qualität:": {
        "de": "PDF-Qualität:", "en": "PDF Quality:", "es": "Calidad de PDF:", "zh": "PDF质量:", "ja": "PDF品質:", "ru": "Качество PDF:"
    },
    "PDF komprimieren": {
        "de": "PDF komprimieren", "en": "Compress PDF", "es": "Comprimir PDF", "zh": "压缩PDF", "ja": "PDF圧縮", "ru": "Сжать PDF"
    },
    "OCR-Einstellungen": {
        "de": "OCR-Einstellungen", "en": "OCR Settings", "es": "Configuración de OCR", "zh": "OCR设置", "ja": "OCR設定", "ru": "Настройки OCR"
    },
    "Tesseract-Pfad:": {
        "de": "Tesseract-Pfad:", "en": "Tesseract Path:", "es": "Ruta de Tesseract:", "zh": "Tesseract路径:", "ja": "Tesseractパス:", "ru": "Путь к Tesseract:"
    },
    "OCR-Auflösung:": {
        "de": "OCR-Auflösung:", "en": "OCR Resolution:", "es": "Resolución OCR:", "zh": "OCR分辨率:", "ja": "OCR解像度:", "ru": "Разрешение OCR:"
    },
    "Cache": {
        "de": "Cache", "en": "Cache", "es": "Caché", "zh": "缓存", "ja": "キャッシュ", "ru": "Кэш"
    },
    "Cache leeren": {
        "de": "Cache leeren", "en": "Clear Cache", "es": "Vaciar caché", "zh": "清理缓存", "ja": "キャッシュをクリア", "ru": "Очистить кэш"
    },

    # Dialog & Message Strings
    "Möchten Sie die Änderungen speichern?": {
        "de": "Möchten Sie die Änderungen speichern?",
        "en": "Do you want to save changes?",
        "es": "¿Desea guardar los cambios?",
        "zh": "您要保存更改吗？",
        "ja": "変更を保存しますか？",
        "ru": "Вы хотите сохранить изменения?"
    },
    "Fehler": {
        "de": "Fehler", "en": "Error", "es": "Error", "zh": "错误", "ja": "エラー", "ru": "Ошибка"
    },
    "Hinweis": {
        "de": "Hinweis", "en": "Notice", "es": "Aviso", "zh": "提示", "ja": "通知", "ru": "Уведомление"
    },
    "Erfolg": {
        "de": "Erfolg", "en": "Success", "es": "Éxito", "zh": "成功", "ja": "成功", "ru": "Успешно"
    },
    "Fertig": {
        "de": "Fertig", "en": "Done", "es": "Listo", "zh": "完成", "ja": "完了", "ru": "Готово"
    },
    "In Zwischenablage kopiert!": {
        "de": "In Zwischenablage kopiert!",
        "en": "Copied to clipboard!",
        "es": "¡Copiado al portapapeles!",
        "zh": "已复制到剪贴板！",
        "ja": "クリップボードにコピーしました！",
        "ru": "Скопировано в буфер обмена!"
    },
    "Keine Datei analysiert": {
        "de": "Keine Datei analysiert",
        "en": "No file analyzed",
        "es": "Ningún archivo analizado",
        "zh": "未分析任何文件",
        "ja": "解析されたファイルはありません",
        "ru": "Файлы не проанализированы"
    },
    "Alle auswählen": {
        "de": "Alle auswählen", "en": "Select All", "es": "Seleccionar todo", "zh": "全选", "ja": "すべて選択", "ru": "Выбрать все"
    },
    "Auswahl aufheben": {
        "de": "Auswahl aufheben", "en": "Clear Selection", "es": "Deseleccionar", "zh": "取消选择", "ja": "選択解除", "ru": "Снять выделение"
    },
    "Auswahl umkehren": {
        "de": "Auswahl umkehren", "en": "Invert Selection", "es": "Invertir selección", "zh": "反向选择", "ja": "選択反転", "ru": "Инвертировать выбор"
    },
    "Alle löschen": {
        "de": "Alle löschen", "en": "Delete All", "es": "Eliminar todo", "zh": "全部删除", "ja": "すべて削除", "ru": "Удалить все"
    },
    "Ausgewählte schwärzen...": {
        "de": "Ausgewählte schwärzen...", "en": "Redact Selected...", "es": "Censurar seleccionados...", "zh": "涂黑选中项...", "ja": "選択項目を墨消し...", "ru": "Скрыть выбранное..."
    },
    "OCR starten": {
        "de": "OCR starten", "en": "Start OCR", "es": "Iniciar OCR", "zh": "开始OCR", "ja": "OCR開始", "ru": "Запустить OCR"
    },
    "Erkannter Text": {
        "de": "Erkannter Text", "en": "Recognized Text", "es": "Texto reconocido", "zh": "识别出的文本", "ja": "認識されたテキスト", "ru": "Распознанный текст"
    },
    "Passwort:": {
        "de": "Passwort:", "en": "Password:", "es": "Contraseña:", "zh": "密码:", "ja": "パスワード:", "ru": "Пароль:"
    },
    "Entsperren": {
        "de": "Entsperren", "en": "Unlock", "es": "Desbloquear", "zh": "解锁", "ja": "ロック解除", "ru": "Разблокировать"
    },
    "PDF exportieren...": {
        "de": "PDF exportieren...", "en": "Export PDF...", "es": "Exportar PDF...", "zh": "导出PDF...", "ja": "PDFエクスポート...", "ru": "Экспорт PDF..."
    }
}

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(TRANSLATIONS, f, indent=2, ensure_ascii=False)

print(f"Generated {len(TRANSLATIONS)} translation entries in {out_file}")
