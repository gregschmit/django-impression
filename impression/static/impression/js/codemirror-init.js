document.addEventListener("DOMContentLoaded", function() {
  /* the Django template editor */
  Array.prototype.forEach.call(document.getElementsByClassName('impression-template-editor'), function(el, i) {
    /* select the theme from the cookie */
    var theme = 'base16-light';
    document.cookie.split(';').forEach(function(cookie) {
      var parts = cookie.split('=');
      if (parts[0].trim() == 'codemirror-theme') {
        theme = parts[1].trim();
      }
    });

    /* select mode from attached class */
    var mode = 0;
    if (el.classList.contains('impression-mode-django')) {
      mode = 'text/x-django';
    } else {
      console.log("ImpressionEditor: No mode found!");
    }

    /* build code mirror text area */
    var cm = CodeMirror.fromTextArea(el, {
      lineNumbers: true,
      mode: mode,
      indentUnit: 2,
      smartIndent: true,
      tabSize: 2,
      theme: theme,
    });
    cm.setSize('60em', '40em');

    /* add theme selector HTML */
    var select_theme = `
      <select style="height: 1.5em;" id="impression-select-theme-${i}">
        <option value="base16-light">Base16 Light</option>
        <option value="base16-dark">Base16 Dark</option>
        <option value="solarized light">Solarized Light</option>
        <option value="solarized dark">Solarized Dark</option>
      </select>
    `;
    el.insertAdjacentHTML('beforebegin', select_theme);

    /* get the select element and set the initial value */
    var ts = document.getElementById(`impression-select-theme-${i}`);
    ts.value = theme;

    /* add theme selector onchange listener */
    ts.addEventListener('change', function() {
      var theme = this.value;
      cm.setOption('theme', theme);
      document.cookie = `codemirror-theme=${theme};path=/;`;
    });
  });
});
