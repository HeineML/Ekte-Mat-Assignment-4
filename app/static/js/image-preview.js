// Shows a preview of the chosen picture before the food item form is saved (A2).
// <input type="file" data-preview="img-id"> updates <img id="img-id">.
document.querySelectorAll("input[type=file][data-preview]").forEach(function (input) {
  var img = document.getElementById(input.dataset.preview);
  var original = img.src;
  var note = document.getElementById(input.dataset.preview + "-note");

  input.addEventListener("change", function () {
    var file = input.files[0];
    if (img.dataset.objectUrl) {
      URL.revokeObjectURL(img.dataset.objectUrl);
      delete img.dataset.objectUrl;
    }
    if (file) {
      img.dataset.objectUrl = URL.createObjectURL(file);
      img.src = img.dataset.objectUrl;
    } else {
      img.src = original;
    }
    if (note) note.hidden = !file;
  });
});
