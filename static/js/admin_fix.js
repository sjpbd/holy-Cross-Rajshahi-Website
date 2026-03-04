console.log("Modern Admin Layout Applied - Stacking Enabled");

(function ($) {
    $(document).ready(function () {
        const fixEditorWidth = () => {
            // Force a window resize event to trigger Summernote's internal width calc
            window.dispatchEvent(new Event('resize'));

            // Aggressively set widths via JS for any missed containers
            $('.django-summernote-widget').css('width', '100%');
            $('.note-editor').css('width', '100%');
            $('.note-frame').css('width', '100%');
            $('.note-editing-area').css('width', '100%');
            $('.note-editable').css('width', '100%');
        };

        // Run immediately
        fixEditorWidth();

        // Run after 1s just in case of slow dynamic loading
        setTimeout(fixEditorWidth, 1000);

        // Final check after 3s
        setTimeout(fixEditorWidth, 3000);
    });
})(window.django ? window.django.jQuery : jQuery);
