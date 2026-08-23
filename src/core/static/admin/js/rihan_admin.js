/* اسکریپت کمکی پوسته ادمین ریحان: منوی موبایل + هایلایت لینک فعال */
(function () {
  "use strict";

  var burger = document.getElementById("rsb-burger");
  var sidebar = document.getElementById("rihan-sidebar");
  var overlay = document.getElementById("rsb-overlay");

  function closeMenu() {
    document.body.classList.remove("rsb-open");
  }

  if (burger) {
    burger.addEventListener("click", function () {
      document.body.classList.toggle("rsb-open");
    });
  }
  if (overlay) overlay.addEventListener("click", closeMenu);

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeMenu();
  });

  // هایلایت آیتم فعال سایدبار بر اساس آدرس فعلی
  var path = window.location.pathname;
  var links = document.querySelectorAll(".rihan-sidebar a[href]");
  for (var i = 0; i < links.length; i++) {
    var href = links[i].getAttribute("href") || "";
    if (!href || href === "#") continue;
    if (href === "/admin/") {
      if (path === "/admin/" || path === "/admin") links[i].classList.add("active");
    } else if (path.indexOf(href) === 0) {
      links[i].classList.add("active");
    }
  }
})();
