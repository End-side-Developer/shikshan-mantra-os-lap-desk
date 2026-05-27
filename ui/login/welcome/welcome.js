/* welcome.js — Local Student closes the page; Institution stays disabled
 * (ADR-0009, SMO-0299). Firstrun marker is managed by the autostart wrapper. */

(function () {
  'use strict';

  var buttons = document.querySelectorAll('.role-button');

  buttons.forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      if (btn.disabled) {
        e.preventDefault();
        return;
      }
      var role = btn.dataset.role;
      if (role === 'local-student') {
        // Local mode: simply dismiss. Wrapper has already written the
        // firstrun marker so we won't be shown again.
        window.close();
      }
      // role === 'institution' is unreachable while the button stays disabled.
    });
  });
})();
