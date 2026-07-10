(function () {
    function reportViewport() {
        var width = window.screen && window.screen.width ? window.screen.width : window.innerWidth;
        var body = new URLSearchParams();
        body.append("width", String(width));
        var csrf = document.querySelector("meta[name=csrf-token]");
        var headers = {"Content-Type": "application/x-www-form-urlencoded"};
        if (csrf) {
            headers["X-CSRFToken"] = csrf.getAttribute("content");
        }
        fetch("/set-viewport/", {method: "POST", body: body.toString(), headers: headers, credentials: "same-origin"});
    }
    reportViewport();
    window.addEventListener("resize", reportViewport);
})();
