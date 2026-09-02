(function () {
    document.addEventListener("DOMContentLoaded", function () {

        const statementSelect = document.getElementById("id_statement");
        const parentSelect = document.getElementById("id_parent");

        if (!statementSelect || !parentSelect) return;

        // Hozirgi tanlangan parent qiymatini saqlaymiz (edit holatida)
        const currentParentId = parentSelect.value;

        /**
         * Parent select optionlarini yangilaydi va Select2 ni refresh qiladi.
         * Jazzmin admin tema Select2 ishlatadi — shuning uchun oddiy
         * innerHTML o'zgartirish yetarli emas.
         */
        function setParentOptions(options, preselect) {
            // 1. Avval Select2 ni destroy qilamiz (agar mavjud bo'lsa)
            try {
                if (window.jQuery && jQuery.fn.select2) {
                    jQuery(parentSelect).select2("destroy");
                }
            } catch (e) {
                // Select2 hali init bo'lmagan bo'lishi mumkin
            }

            // 2. Oddiy <select> optionlarni yangilaymiz
            parentSelect.innerHTML = "";

            const emptyOpt = document.createElement("option");
            emptyOpt.value = "";
            emptyOpt.textContent = "---------";
            parentSelect.appendChild(emptyOpt);

            options.forEach(function (p) {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = p.name;
                if (preselect && String(p.id) === String(preselect)) {
                    opt.selected = true;
                }
                parentSelect.appendChild(opt);
            });

            // 3. Select2 ni qayta ishga tushiramiz
            try {
                if (window.jQuery && jQuery.fn.select2) {
                    jQuery(parentSelect).select2({
                        theme: "bootstrap4",
                        placeholder: "---------",
                        allowClear: true,
                    });
                }
            } catch (e) {
                console.warn("Select2 reinit xatosi:", e);
            }
        }

        function loadParents(statementId, preselect) {
            if (!statementId) {
                setParentOptions([], null);
                return;
            }

            // Absolute URL: /admin/reports/plant/load-parents/
            var baseUrl = window.location.pathname
                .replace(/\/(add\/|[\w-]+\/change\/).*$/, "/");

            fetch(baseUrl + "load-parents/?statement=" + statementId)
                .then(function (r) {
                    if (!r.ok) throw new Error("HTTP " + r.status);
                    return r.json();
                })
                .then(function (data) {
                    setParentOptions(data, preselect);
                })
                .catch(function (err) {
                    console.error("load-parents xatosi:", err);
                    setParentOptions([], null);
                });
        }

        // ── Statement uchun ham Select2 change eventini eshitamiz ──
        // Jazzmin Select2 "change" eventini jQuery orqali yuboradi,
        // shuning uchun ikkala eventni ham eshitamiz.

        // Standard DOM event
        statementSelect.addEventListener("change", function () {
            loadParents(this.value, null);
        });

        // jQuery Select2 change event (Jazzmin uchun)
        if (window.jQuery) {
            jQuery(statementSelect).on("change.select2", function () {
                loadParents(this.value, null);
            });
        }

        // ── Sahifa ochilganda ──
        // Kichik kutish — Select2 init bo'lishini kutamiz
        setTimeout(function () {
            if (statementSelect.value) {
                loadParents(statementSelect.value, currentParentId);
            } else {
                setParentOptions([], null);
            }
        }, 300);

    });
})();