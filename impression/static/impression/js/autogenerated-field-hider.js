document.addEventListener("DOMContentLoaded", function() {
  /*
   * This script handles the logic of hiding the plaintext body field if the
   * `autogenerate_plaintext_body` checkbox is selected.
   */

  /* define the function that sets the visibility of the field */
  console.log("here");
  function setPlainTextVisibility() {
    field = document.getElementsByClassName('field-body_plaintext')[0];
    checkbox = document.getElementById('id_autogenerate_plaintext_body');
    if (checkbox.checked) {
      field.style.display = 'none';
    } else {
      field.style.display = 'block';
    }
  }

  /* run it now to set initial state */
  setPlainTextVisibility();

  /* add listener to checkbox */
  checkbox = document.getElementById('id_autogenerate_plaintext_body');
  checkbox.addEventListener('change', setPlainTextVisibility);
});
