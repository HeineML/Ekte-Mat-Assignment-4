// Guest groups on the checkout form (C3). Without JavaScript the form shows one row and works as before.
// With it, a checkbox shows or hides the groups, and "Add group"/"Remove" change the number of rows.
// Hidden rows are disabled, so they are not sent with the order.
(function () {
  var toggle = document.getElementById("has-groups");
  var section = document.getElementById("guest-group-rows");
  if (!toggle || !section) return;
  var list = section.querySelector(".guest-group-list");
  var template = document.getElementById("guest-group-template");
  var addButton = section.querySelector(".add-group");

  function setUp(row) {
    var remove = row.querySelector(".remove-group");
    remove.hidden = false;
    remove.addEventListener("click", function () {
      if (list.children.length > 1) {
        row.remove();
      } else {
        row.querySelectorAll("input").forEach(function (input) { input.value = ""; });
      }
    });
  }

  function update() {
    section.hidden = !toggle.checked;
    section.querySelectorAll("input").forEach(function (input) { input.disabled = !toggle.checked; });
  }

  Array.prototype.forEach.call(list.children, setUp);
  addButton.hidden = false;
  addButton.addEventListener("click", function () {
    var row = template.content.firstElementChild.cloneNode(true);
    list.appendChild(row);
    setUp(row);
    update();
    row.querySelector("input").focus();
  });

  toggle.closest("label").hidden = false;
  toggle.addEventListener("change", update);
  update();
})();
