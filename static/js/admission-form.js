(function () {
    var BENGALI_ERROR = 'শুধু বাংলা অক্ষরে লিখুন / Use Bengali characters only.';
    var BIRTH_ERROR = 'Birth registration number must be 13, 16, or 17 digits.';
    var PHONE_ERROR = 'Phone number must be 11 digits (01XXXXXXXXX).';
    var REQUIRED_ERROR = 'This field is required.';
    var HAS_BENGALI = /[\u0980-\u09FF]/;
    var HAS_LATIN = /[A-Za-z]/;
    var BENGALI_OK = /^[\u0980-\u09FF\s।॥\-–.,()]+$/;

    function digits(value) {
        return String(value || '').replace(/\D/g, '');
    }

    function wrapOf(el) {
        return el.closest('.adm-field') || el.closest('.adm-section') || el.parentElement;
    }

    function clearJsError(wrap) {
        if (!wrap) return;
        wrap.querySelectorAll('.adm-error.js').forEach(function (node) { node.remove(); });
        if (!wrap.querySelector('.adm-error')) wrap.classList.remove('is-invalid');
    }

    function setJsError(wrap, message) {
        if (!wrap) return;
        wrap.classList.add('is-invalid');
        var err = wrap.querySelector('.adm-error.js');
        if (!err) {
            err = document.createElement('p');
            err.className = 'adm-error js';
            wrap.appendChild(err);
        }
        err.textContent = message;
    }

    function checkBengali(el) {
        var wrap = wrapOf(el);
        var value = (el.value || '').trim();
        if (!value) {
            clearJsError(wrap);
            return true;
        }
        if (HAS_LATIN.test(value) || !HAS_BENGALI.test(value) || !BENGALI_OK.test(value)) {
            setJsError(wrap, BENGALI_ERROR);
            return false;
        }
        clearJsError(wrap);
        return true;
    }

    function checkBirth(el) {
        var wrap = wrapOf(el);
        var value = digits(el.value);
        if (!value) {
            clearJsError(wrap);
            return true;
        }
        if ([13, 16, 17].indexOf(value.length) === -1) {
            setJsError(wrap, BIRTH_ERROR);
            return false;
        }
        clearJsError(wrap);
        return true;
    }

    function checkPhone(el) {
        var wrap = wrapOf(el);
        var value = digits(el.value);
        if (value.length === 13 && value.indexOf('880') === 0) value = value.slice(3);
        if (!value) {
            clearJsError(wrap);
            return true;
        }
        if (!(value.length === 11 && value.indexOf('01') === 0 && '3456789'.indexOf(value.charAt(2)) !== -1)) {
            setJsError(wrap, PHONE_ERROR);
            return false;
        }
        clearJsError(wrap);
        return true;
    }

    function isVisible(el) {
        if (!el || el.disabled) return false;
        var node = el;
        while (node && node !== document.body) {
            if (node.classList && node.classList.contains('hidden')) return false;
            node = node.parentElement;
        }
        return true;
    }

    function fieldValue(el) {
        if (el.type === 'radio') {
            var checked = document.querySelector('input[name="' + el.name + '"]:checked');
            return checked ? checked.value : '';
        }
        if (el.type === 'checkbox') return el.checked ? 'on' : '';
        if (el.type === 'file') return el.files && el.files.length ? 'file' : (el.closest('[data-photo]') && el.closest('[data-photo]').getAttribute('data-photo')) || '';
        return (el.value || '').trim();
    }

    function isSkippedPermanent(el, form) {
        var copy = form.querySelector('#id_copy_same_permanent');
        if (!copy || !copy.checked) return false;
        var name = el.name || '';
        return name.indexOf('permanent_') === 0;
    }

    function requiredEmpty(el, form) {
        if (!isVisible(el) || el.disabled) return false;
        if (isSkippedPermanent(el, form)) return false;
        if (el.classList && el.classList.contains('adm-radios')) {
            return !el.querySelector('input[type="radio"]:checked');
        }
        if (el.type === 'radio') {
            var checked = document.querySelector('input[name="' + el.name + '"]:checked');
            return !(checked && checked.value);
        }
        if (el.type === 'checkbox') return false;
        if (el.type === 'file') {
            if (el.files && el.files.length) return false;
            var host = el.closest('[data-photo]');
            return !(host && host.getAttribute('data-photo'));
        }
        return !(el.value || '').trim();
    }

    function validateRequired(form) {
        var first = null;
        var seenRadios = {};

        form.querySelectorAll('.adm-field[data-required-field="true"]').forEach(function (wrap) {
            if (!isVisible(wrap)) return;
            var group = wrap.querySelector('.adm-radios');
            if (!group) return;
            group.querySelectorAll('input[type="radio"]').forEach(function (radio) {
                seenRadios[radio.name] = true;
            });
            if (!group.querySelector('input[type="radio"]:checked')) {
                setJsError(wrap, REQUIRED_ERROR);
                if (!first) first = wrap;
            }
        });

        form.querySelectorAll('[data-required="true"]').forEach(function (el) {
            if (el.classList && el.classList.contains('adm-radios')) return;
            if (el.type === 'radio') {
                if (seenRadios[el.name]) return;
                seenRadios[el.name] = true;
            }
            if (!requiredEmpty(el, form)) {
                return;
            }
            var wrap = wrapOf(el);
            var message = REQUIRED_ERROR;
            if (el.type === 'file' || (el.name && el.name.indexOf('photo') !== -1)) {
                message = 'Please upload a passport photo.';
            }
            setJsError(wrap, message);
            if (!first) first = wrap;
        });
        if (first && first.scrollIntoView) {
            first.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return !first;
    }

    function classCode(select, map) {
        if (!select || !select.value) return '';
        return map[String(select.value)] || '';
    }

    function toggleClassExtras(form, map) {
        var select = form.querySelector('#id_admit_class');
        if (!select) return;
        var code = classCode(select, map);
        var class6 = document.getElementById('class6RegWrap');
        var class8 = document.getElementById('class8RegWrap');
        var group = document.getElementById('studyGroupWrap');
        var show6 = code === 'class-7' || code === 'class-8' || code === 'class-9';
        var show9 = code === 'class-9';
        if (class6) class6.classList.toggle('hidden', !show6);
        if (class8) class8.classList.toggle('hidden', !show9);
        if (group) group.classList.toggle('hidden', !show9);
        [class6, class8, group].forEach(function (wrap) {
            if (!wrap) return;
            wrap.querySelectorAll('input, select').forEach(function (el) {
                el.disabled = wrap.classList.contains('hidden');
            });
        });
    }

    function syncGuardian(form) {
        var wrap = document.getElementById('guardianOtherWrap');
        var note = document.getElementById('guardianCopyNote');
        if (!wrap && !note) return;
        var checked = form.querySelector('input[name="guardian_type"]:checked');
        var value = checked ? checked.value : '';
        var other = value === 'other';
        if (wrap) {
            wrap.classList.toggle('hidden', !other);
            wrap.querySelectorAll('input, select, textarea').forEach(function (el) {
                el.disabled = !other;
            });
        }
        if (note) {
            var father = ((form.querySelector('#id_father_name') || {}).value || '').trim();
            var mother = ((form.querySelector('#id_mother_name') || {}).value || '').trim();
            if (value === 'father') {
                note.textContent = 'Guardian will be ' + (father || 'the father') + ' (Father).';
                note.classList.remove('hidden');
            } else if (value === 'mother') {
                note.textContent = 'Guardian will be ' + (mother || 'the mother') + ' (Mother).';
                note.classList.remove('hidden');
            } else {
                note.textContent = '';
                note.classList.add('hidden');
            }
        }
    }

    function bindLive(form) {
        form.querySelectorAll('[data-validate="bengali"]').forEach(function (el) {
            el.addEventListener('input', function () { checkBengali(el); });
            el.addEventListener('blur', function () { checkBengali(el); });
        });
        form.querySelectorAll('[data-validate="birth"]').forEach(function (el) {
            el.addEventListener('input', function () { checkBirth(el); });
            el.addEventListener('blur', function () { checkBirth(el); });
        });
        form.querySelectorAll('[data-validate="phone"]').forEach(function (el) {
            el.addEventListener('input', function () { checkPhone(el); });
            el.addEventListener('blur', function () { checkPhone(el); });
        });
    }

    function classMap() {
        var el = document.getElementById('class-codes-data');
        if (!el) return {};
        try { return JSON.parse(el.textContent); } catch (err) { return {}; }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var forms = document.querySelectorAll('form.adm-wizard-form');
        var map = classMap();
        forms.forEach(function (form) {
            bindLive(form);
            toggleClassExtras(form, map);
            syncGuardian(form);
            var classSelect = form.querySelector('#id_admit_class');
            if (classSelect) {
                classSelect.addEventListener('change', function () { toggleClassExtras(form, map); });
            }
            form.querySelectorAll('input[name="guardian_type"]').forEach(function (el) {
                el.addEventListener('change', function () { syncGuardian(form); });
            });
            ['#id_father_name', '#id_mother_name'].forEach(function (selector) {
                var input = form.querySelector(selector);
                if (input) input.addEventListener('input', function () { syncGuardian(form); });
            });
            form.addEventListener('submit', function (event) {
                var liveOk = true;
                form.querySelectorAll('[data-validate="bengali"]').forEach(function (el) {
                    if (isVisible(el) && (el.value || '').trim() && !checkBengali(el)) liveOk = false;
                });
                form.querySelectorAll('[data-validate="birth"]').forEach(function (el) {
                    if (isVisible(el) && (el.value || '').trim() && !checkBirth(el)) liveOk = false;
                });
                form.querySelectorAll('[data-validate="phone"]').forEach(function (el) {
                    if (isVisible(el) && (el.value || '').trim() && !checkPhone(el)) liveOk = false;
                });
                var requiredOk = validateRequired(form);
                if (!liveOk || !requiredOk) event.preventDefault();
            });
            form.addEventListener('change', function (event) {
                var el = event.target;
                if (!el) return;
                if (!requiredEmpty(el, form)) {
                    var wrap = wrapOf(el);
                    if (!wrap) return;
                    wrap.querySelectorAll('.adm-error.js').forEach(function (node) {
                        if (node.textContent === REQUIRED_ERROR || node.textContent.indexOf('passport photo') !== -1) {
                            node.remove();
                        }
                    });
                    if (!wrap.querySelector('.adm-error')) wrap.classList.remove('is-invalid');
                }
            });
        });
        var firstError = document.querySelector('.adm-field.is-invalid, .adm-error');
        if (firstError && firstError.scrollIntoView) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });
})();
