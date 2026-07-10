(function () {
    function setViewportCookie() {
        var width = window.screen && window.screen.width ? window.screen.width : window.innerWidth;
        document.cookie = "desktap_viewport_width=" + width + ";path=/;SameSite=Lax";
    }
    setViewportCookie();
    window.addEventListener("resize", setViewportCookie);
})();
