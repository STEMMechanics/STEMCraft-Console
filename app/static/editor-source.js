import {basicSetup} from "codemirror";
import {EditorState} from "@codemirror/state";
import {EditorView, keymap} from "@codemirror/view";
import {indentUnit} from "@codemirror/language";
import {indentWithTab} from "@codemirror/commands";
import {lintGutter, setDiagnostics} from "@codemirror/lint";
import {css} from "@codemirror/lang-css";
import {html} from "@codemirror/lang-html";
import {javascript} from "@codemirror/lang-javascript";
import {json} from "@codemirror/lang-json";
import {markdown} from "@codemirror/lang-markdown";
import {sql} from "@codemirror/lang-sql";
import {xml} from "@codemirror/lang-xml";
import {yaml} from "@codemirror/lang-yaml";

function languageFor(filename) {
  const lower = String(filename || "").toLowerCase();
  if (lower.endsWith(".json") || lower.endsWith(".map")) return {name: "JSON", extension: json()};
  if (lower.endsWith(".yml") || lower.endsWith(".yaml")) return {name: "YAML", extension: yaml()};
  if (lower.endsWith(".html") || lower.endsWith(".htm")) return {name: "HTML", extension: html()};
  if (lower.endsWith(".xml")) return {name: "XML", extension: xml()};
  if (lower.endsWith(".css")) return {name: "CSS", extension: css()};
  if (lower.endsWith(".js")) return {name: "JavaScript", extension: javascript()};
  if (lower.endsWith(".md")) return {name: "Markdown", extension: markdown()};
  if (lower.endsWith(".sql")) return {name: "SQL", extension: sql()};
  return {name: "Plain text", extension: []};
}

const stemcraftTheme = EditorView.theme({
  "&": {height: "100%", backgroundColor: "#17191e", color: "#d6d9de"},
  ".cm-content": {caretColor: "#ffffff", fontFamily: '"SFMono-Regular", Consolas, monospace'},
  ".cm-cursor, .cm-dropCursor": {borderLeftColor: "#ffffff"},
  ".cm-gutters": {backgroundColor: "#121419", color: "#777d88", border: "none"},
  ".cm-activeLine, .cm-activeLineGutter": {backgroundColor: "#20232a"},
  ".cm-selectionBackground, &.cm-focused .cm-selectionBackground": {backgroundColor: "#34445f"},
  ".cm-tooltip": {backgroundColor: "#252932", color: "#e6e9ef", borderColor: "#3a3f49"},
  ".cm-diagnostic-warning": {borderLeftColor: "#e5a52f"},
}, {dark: true});

function create(textarea, options = {}) {
  if (!textarea || textarea.dataset.codeEditorReady === "true") return textarea?._codeEditor;
  const language = languageFor(options.filename || textarea.dataset.filename);
  const indentation = " ".repeat(options.indentSize || (language.name === "YAML" ? 2 : 4));
  const host = document.createElement("div");
  host.className = "code-editor-host";
  textarea.before(host);
  textarea.classList.add("code-editor-source");
  textarea.dataset.codeEditorReady = "true";

  const saveKey = {
    key: "Mod-s",
    preventDefault: true,
    run: () => {
      if (options.onSave) options.onSave();
      else textarea.form?.requestSubmit(textarea.form.querySelector('[data-editor-save="true"]'));
      return true;
    },
  };
  const view = new EditorView({
    parent: host,
    state: EditorState.create({
      doc: textarea.value,
      extensions: [
        basicSetup,
        language.extension,
        indentUnit.of(indentation),
        EditorState.tabSize.of(4),
        keymap.of([saveKey, indentWithTab]),
        lintGutter(),
        stemcraftTheme,
        EditorView.updateListener.of((update) => {
          if (update.docChanged) textarea.value = update.state.doc.toString();
        }),
      ],
    }),
  });
  textarea._codeEditor = view;
  host.dataset.language = language.name;
  if (options.languageLabel) options.languageLabel.textContent = language.name;
  if (options.warning) showWarning(view, options.warning);
  return view;
}

function showWarning(view, warning) {
  if (!view) return;
  if (!warning?.message) {
    view.dispatch(setDiagnostics(view.state, []));
    return;
  }
  const requestedLine = Number(warning.line) || 1;
  const lineNumber = Math.max(1, Math.min(requestedLine, view.state.doc.lines));
  const line = view.state.doc.line(lineNumber);
  const column = Math.max(1, Number(warning.column) || 1);
  const from = Math.min(line.to, line.from + column - 1);
  const to = Math.min(line.to, Math.max(from + 1, from));
  view.dispatch(setDiagnostics(view.state, [{
    from,
    to,
    severity: "warning",
    message: warning.message,
  }]));
  view.dispatch({selection: {anchor: from}, scrollIntoView: true});
}

window.STEMCodeEditor = {create, showWarning, languageFor};
window.dispatchEvent(new CustomEvent("stemcraft:editor-ready"));
