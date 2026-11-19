import html
import html as html_lib
import json
import re
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QUrl, QUrlQuery, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView

_APP_BASE_URL = QUrl(Path(__file__).resolve().parent.parent.as_uri() + "/")

# Rendu Markdown fidèle (CommonMark, retours à la ligne, tableaux, code).
# Installation : pip install markdown-it-py
try:
    from markdown_it import MarkdownIt
    from pygments import highlight as pygments_highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import HtmlFormatter

    # Configuration du thème syntaxique
    _PYGMENTS_FORMATTER = HtmlFormatter(
        style="dracula",
        nowrap=True
    )

    def highlight_code(code, language, attrs):
        if not language:
            return ""

        try:
            lexer = get_lexer_by_name(language)
            return pygments_highlight(
                code,
                lexer,
                _PYGMENTS_FORMATTER
            )
        except Exception:
            # Langage inconnu : affichage normal
            return ""


    _MD = MarkdownIt(
        "commonmark",
        {
            "breaks": True,
            "html": False,
            "highlight": highlight_code
        }
    ).enable(["table", "strikethrough"])

except ImportError:
    _MD = None
    _PYGMENTS_FORMATTER = None

def render_code_block(tokens, idx, options, env):
    token = tokens[idx]

    # Récupération du langage
    info = token.info.strip()
    language, _, name = info.partition(" ")
    language = language or "text"
    name = name.strip()
    named_program = re.search(
        r"(?:title|filename)\s*=\s*(['\"])(.*?)\1",
        name,
        flags=re.IGNORECASE,
    )
    if named_program:
        name = named_program.group(2)
    elif name.lower().startswith(("title=", "filename=")):
        name = name.split("=", 1)[1].strip("'\"")

    # Coloration syntaxique
    highlighted = highlight_code(
        token.content,
        language,
        ""
    )

    # Si Pygments ne reconnaît pas le langage
    if not highlighted:
        highlighted = html.escape(token.content)

    return f"""
    <div class="code-block"
         data-language="{html.escape(language, quote=True)}"
         data-name="{html.escape(name, quote=True)}">
        <div class="code-toolbar">
            <span class="code-language">{html.escape(language.upper())}</span>

            <div display="flex">
                <button class="open-code" onclick="openCode(this)" type="button">
                    <img src="Icons/arrow-up-right-from-square-solid-full.svg" alt="" class="open-icon">
                </button>
                <button class="copy-code" onclick="copyCode(this)" type="button">
                    <img src="Icons/copy-solid-full.svg" alt="" class="copy-icon">
                </button>
            </div>
        </div>

        <pre><code>{highlighted}</code></pre>
    </div>
    """


if _MD is not None:
    _MD.renderer.rules["fence"] = render_code_block
def prepare_markdown_for_qt(markdown):
    """Force les retours à la ligne simples sans toucher aux blocs de code."""
    lines = (markdown or "").replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ").split("\n")
    result = []
    in_fence = False
    fence_marker = None

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = None
            result.append(line)
            continue

        if in_fence or not line.strip():
            result.append(line)
            continue

        # Deux espaces avant le saut : rendu Markdown en retour forcé.
        result.append(line.rstrip() + "  ")

    return "\n".join(result)
MARKDOWN_CSS = """
<style>
    html, body {
        background: transparent;
        color: #D7F8FF;
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
        line-height: 1.52;
        margin: 0;
        padding: 0;
        overflow-wrap: anywhere;
    }
    html { overflow: hidden; }
    body { padding: 3px 2px 5px; }
    p { margin: 5px 0 8px; }
    p:first-child { margin-top: 0; }
    p:last-child { margin-bottom: 0; }
    h1, h2, h3, h4 { color: #36DDFB; line-height: 1.25; }
    h1 { font-size: 1.35em; margin: 12px 0 7px; }
    h2 { font-size: 1.2em; margin: 11px 0 6px; }
    h3, h4 { font-size: 1.08em; margin: 9px 0 5px; }
    a { color: #55E7FF; text-decoration: none; }
    a:hover { text-decoration: underline; }
    blockquote {
        color: #A6D3DC; border-left: 3px solid #00AFCF;
        padding: 2px 0 2px 10px; margin: 8px 0;
    }
    pre {
        box-sizing: border-box; white-space: pre-wrap; overflow-wrap: anywhere;
        background: #050D14; color: #D7F8FF;
        border: 1px solid #145064; border-radius: 5px;
        padding: 11px; margin: 8px 0;
        font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px;
    }
    pre code { background: transparent; padding: 0; border-radius: 0; }
    code {
        background: #0A202B; color: #69E9FF; padding: 2px 4px;
        border-radius: 3px; font-family: 'Cascadia Code', 'Consolas', monospace;
    }
    .code-block {
        background: #050D14; border: 1px solid #176078;
        border-radius: 5px; overflow: hidden; margin: 10px 0;
    }
    .code-toolbar {
        display: flex; align-items: center; justify-content: space-between;
        padding: 7px 12px; background: #0B202B;
        border-bottom: 1px solid #145064;
    }
    .code-language {
        color: #36DDFB; font-family: 'Segoe UI', sans-serif;
        font-size: 11px; font-weight: 700; letter-spacing: 1px;
    }
    .copy-code {
        margin-left: 3px;
        border: 1px solid #176078;
        background: transparent;
        border-radius: 4px;
        padding: 4px 12px;
        color: #9CCBD5;
        font-family: 'Segoe UI', sans-serif;
        font-size: 11px;
        cursor: pointer;
        transition: background .18s ease, color .18s ease, border-color .18s ease;
    }
    .copy-icon { width: 18px; height: 18px; vertical-align: middle; }
    .open-icon { width: 18px; height: 18px; vertical-align: middle; }
    .open-code {
        border: 1px solid #176078;
        background: transparent;
        border-radius: 4px;
        padding: 4px 12px;
        color: #9CCBD5;
        font-family: 'Segoe UI', sans-serif;
        font-size: 11px;
        cursor: pointer;
    }
    .open-code:hover { background: #145064; color: #FFFFFF; }
    .copy-code:hover { background: #145064; color: #FFFFFF; }
    .copy-code.copied {
        background: #183D2B;
        border-color: #2E9D62;
        color: #8BE0AD;
    }
    .code-block pre {
        margin: 0;
        border: none;
        border-radius: 0;
        white-space: pre;
        overflow-wrap: normal;
        overflow-x: auto;
    }
    ul, ol { margin: 5px 0 8px; padding-left: 23px; }
    li { margin: 2px 0; }
    hr { border: 0; border-top: 1px solid #145064; margin: 10px 0; }
    table { border-collapse: collapse; width: 100%; margin: 8px 0; }
    th, td { border: 1px solid #145064; padding: 5px 8px; text-align: left; }
    th { background: #0B2632; color: #D7F8FF; }
    img { max-width: 100%; }
</style>
"""
if _PYGMENTS_FORMATTER is not None:
    MARKDOWN_CSS = MARKDOWN_CSS.replace(
        "</style>",
        _PYGMENTS_FORMATTER.get_style_defs("pre code") + "\n</style>",
    )
COPY_JS_FUNCTION = """
<script>
function copyCode(button) {
    const block = button.closest(".code-block");
    const codeElement = block && block.querySelector("pre code");
    const icon = button.querySelector(".copy-icon");

    if (!codeElement || !icon) {
        return;
    }

    // execCommand("copy") fonctionne dans le contexte du clic
    // et évite les restrictions de navigator.clipboard dans Qt WebEngine.
    const textArea = document.createElement("textarea");
    textArea.value = codeElement.innerText;
    textArea.setAttribute("readonly", "");
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    textArea.style.top = "0";

    document.body.appendChild(textArea);
    textArea.select();
    textArea.setSelectionRange(0, textArea.value.length);

    let copied = false;
    try {
        copied = document.execCommand("copy");
    } catch (error) {
        copied = false;
    }

    textArea.remove();

    if (copied) {
        icon.src = "Icons/copy-regular-full.svg";
        button.classList.add("copied");

        if (button._copyTimer) {
            clearTimeout(button._copyTimer);
        }

        button._copyTimer = setTimeout(() => {
            icon.src = "Icons/copy-solid-full.svg";
            button.classList.remove("copied");
            button._copyTimer = null;
        }, 2000);
    } else {
        button.classList.remove("copied");
    }
}

function openCode(button) {
    const block = button.closest(".code-block");
    const codeElement = block.querySelector("pre code");

    if (codeElement) {
        window.location.href = "jarvis://open-code?code="
            + encodeURIComponent(codeElement.innerText)
            + "&language=" + encodeURIComponent(block.dataset.language)
            + "&name=" + encodeURIComponent(block.dataset.name);
    }
}
</script>
"""


class MarkdownPage(QWebEnginePage):
    custom_url_requested = pyqtSignal(QUrl)

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        if url.scheme() == "jarvis" and url.host() == "open-code":
            self.custom_url_requested.emit(url)
            return False
        return super().acceptNavigationRequest(url, navigation_type, is_main_frame)


def markdown_to_html_full(markdown):
    """Construit une page HTML autonome destinée à QWebEngineView."""
    text = (markdown or "").replace("\r\n", "\n").replace("\r", "\n")

    # Pendant le streaming, un bloc de code peut être momentanément incomplet.
    fences = sum(1 for line in text.split("\n") if line.lstrip().startswith("```"))
    if fences % 2:
        text += "\n```"

    if _MD is not None:
        html_body = _MD.render(text)
    else:
        html_body = "<pre>" + html_lib.escape(text) + "</pre>"

    return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            + MARKDOWN_CSS
            + COPY_JS_FUNCTION
            + "</head><body>" + html_body + "</body></html>"
    )
class MarkdownWebView(QWebEngineView):
    """Vue Markdown persistante : le document Chromium n'est chargé qu'une fois."""

    content_size_changed = pyqtSignal(int, int)  # largeur naturelle, hauteur
    open_content_requested = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        page = MarkdownPage(self)
        page.custom_url_requested.connect(self._on_custom_url_requested)
        self.setPage(page)
        self._html_generation = 0
        self._last_size = (0, 0)
        self._page_initialized = False
        self._page_ready = False
        self._pending_body_html = None
        self._markdown_source = ""
        # Re-mesure (anti-rebond) après chaque changement de largeur de la vue.
        self._measure_timer = QTimer(self)
        self._measure_timer.setSingleShot(True)
        self._measure_timer.setInterval(40)
        self._measure_timer.timeout.connect(self._measure_content)

        self.setStyleSheet("background: transparent; border: none;")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.loadFinished.connect(self._on_page_loaded)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    def _on_custom_url_requested(self, url):
        query = QUrlQuery(url)
        code = query.queryItemValue(
            "code", QUrl.ComponentFormattingOption.FullyDecoded
        )
        language = query.queryItemValue(
            "language", QUrl.ComponentFormattingOption.FullyDecoded
        )
        name = query.queryItemValue(
            "name", QUrl.ComponentFormattingOption.FullyDecoded
        )
        self.open_content_requested.emit("programme", {
            "code": code,
            "language": language,
            "name": name,
        })

    def _measure_height(self):
        """Alias conservé pour les anciens appels : mesure largeur + hauteur."""
        self._measure_content()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Quand la largeur change, le texte est re-découpé : la hauteur doit être re-mesurée.
        if event.size().width() != event.oldSize().width():
            self._measure_timer.start()

    @staticmethod
    def _body_html(markdown):
        text = (markdown or "").replace("\r\n", "\n").replace("\r", "\n")
        # Ferme provisoirement un bloc de code incomplet pendant le streaming.
        fences = sum(1 for line in text.split("\n") if line.lstrip().startswith("```"))
        if fences % 2:
            text += "\n```"
        if _MD is not None:
            return _MD.render(text)
        return "<pre>" + html_lib.escape(text) + "</pre>"

    def set_markdown(self, markdown):
        self._markdown_source = markdown or ""
        body_html = self._body_html(self._markdown_source)
        self._html_generation += 1

        # Le premier chargement crée le document et applique le CSS.
        # Ensuite, seul le contenu du body est remplacé via JavaScript :
        # pas de navigation Chromium, donc pas de flash blanc/rechargement.
        if not self._page_initialized:
            self._page_initialized = True
            self._pending_body_html = body_html
            self.setHtml(markdown_to_html_full(""), _APP_BASE_URL)
        elif not self._page_ready:
            self._pending_body_html = body_html
        else:
            self._inject_body_html(body_html)

    def append_markdown(self, text):
        self.set_markdown(self._markdown_source + str(text))

    def _on_page_loaded(self, ok=True):
        if not ok:
            return
        self._page_ready = True
        if self._pending_body_html is not None:
            body_html = self._pending_body_html
            self._pending_body_html = None
            self._inject_body_html(body_html)
        else:
            self._measure_content(self._html_generation)

    def _inject_body_html(self, body_html):
        generation = self._html_generation
        # json.dumps produit une chaîne JavaScript correctement échappée,
        # même si le Markdown contient des guillemets ou des retours à la ligne.
        encoded_html = json.dumps(body_html, ensure_ascii=False)
        script = f"document.body.innerHTML = {encoded_html}; true;"

        def updated(_result):
            if generation == self._html_generation:
                self._measure_content(generation)

        self.page().runJavaScript(script, updated)

    def _measure_content(self, generation=None):
        if not self._page_ready:
            return
        if generation is None:
            generation = self._html_generation

        # IMPORTANT : on mesure le <body> lui-même. root.scrollHeight vaut au minimum la
        # hauteur de la vue, donc une bulle ne pouvait jamais rétrécir. La largeur naturelle
        # est la largeur « max-content » : elle ne dépend pas de la largeur actuelle de la vue
        # (sinon la bulle s'élargissait en boucle jusqu'au maximum).
        script = r"""(() => {
            const body = document.body;
            const previous = body.style.width;
            body.style.width = 'max-content';
            const natural = Math.ceil(body.getBoundingClientRect().width);
            body.style.width = previous;
            const height = Math.ceil(body.getBoundingClientRect().height);
            return {width: Math.max(40, natural), height: height + 2};
        })();"""

        def received(result):
            if generation != self._html_generation or not isinstance(result, dict):
                return
            width = max(40, int(result.get("width", 40)))
            height = max(28, int(result.get("height", 28)))
            if (width, height) != self._last_size:
                self._last_size = (width, height)
                self.content_size_changed.emit(width, height)

        self.page().runJavaScript(script, received)
def render_markdown(view, markdown):
    """Envoie le Markdown à la page HTML de la vue WebEngine."""
    view.set_markdown(markdown)
