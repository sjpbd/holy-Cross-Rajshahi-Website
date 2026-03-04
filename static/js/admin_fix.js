console.log("Holy Cross Admin Fixes Loaded");

(function ($) {
    $(document).ready(function () {
        // Force Summernote to recalculate width after a short delay
        setTimeout(function () {
            window.dispatchEvent(new Event('resize'));
            $('.note-editor').css('width', '100%');
        }, 1000);
    });
})(django.jQuery);
