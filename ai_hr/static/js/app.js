(function () {
    "use strict";

    const api = {
        list: () => fetchJSON("/api/rows"),
        create: (body) => fetchJSON("/api/rows", { method: "POST", body }),
        update: (id, body) => fetchJSON(`/api/rows/${id}`, { method: "PUT", body }),
        del: (id) => fetchJSON(`/api/rows/${id}`, { method: "DELETE" }),
        uploadResume: (id, file) => {
            const fd = new FormData();
            fd.append("file", file);
            return fetchJSON(`/api/rows/${id}/resume`, { method: "POST", formData: fd });
        },
        bulkUpload: (files, jd, focus) => {
            const fd = new FormData();
            for (const f of files) fd.append("files", f);
            if (jd) fd.append("job_desc", jd);
            if (focus) fd.append("focus_points", focus);
            return fetchJSON("/api/rows/bulk_resume", { method: "POST", formData: fd });
        },
        genQuestions: (id) =>
            fetchJSON(`/api/rows/${id}/generate_questions`, { method: "POST" }),
        analyze: (id) => fetchJSON(`/api/rows/${id}/analyze`, { method: "POST" }),
    };

    async function fetchJSON(url, opts = {}) {
        const init = { method: opts.method || "GET", headers: {} };
        if (opts.formData) {
            init.body = opts.formData;
        } else if (opts.body !== undefined) {
            init.headers["Content-Type"] = "application/json";
            init.body = JSON.stringify(opts.body);
        }
        const res = await fetch(url, init);
        let data = null;
        try { data = await res.json(); } catch (_) { /* ignore */ }
        if (!res.ok) {
            const msg = (data && data.error) || `HTTP ${res.status}`;
            throw new Error(msg);
        }
        return data;
    }

    // ---------- state ----------
    const state = { rows: [] };

    // ---------- utils ----------
    const $ = (sel, root) => (root || document).querySelector(sel);
    const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
    const el = (tag, attrs = {}, children = []) => {
        const node = document.createElement(tag);
        for (const [k, v] of Object.entries(attrs)) {
            if (k === "class") node.className = v;
            else if (k === "dataset") Object.assign(node.dataset, v);
            else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
            else if (v !== undefined && v !== null) node.setAttribute(k, v);
        }
        for (const c of [].concat(children)) {
            if (c == null) continue;
            node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
        }
        return node;
    };

    function toast(msg, kind = "") {
        const t = $("#toast");
        t.textContent = msg;
        t.className = `toast show ${kind}`;
        clearTimeout(toast._h);
        toast._h = setTimeout(() => { t.className = "toast"; }, 3000);
    }

    function debounce(fn, ms = 600) {
        let h;
        return function (...args) {
            clearTimeout(h);
            h = setTimeout(() => fn.apply(this, args), ms);
        };
    }

    // Minimal markdown renderer (headings, bold, italic, code, lists, line-breaks)
    function renderMarkdown(src) {
        if (!src) return "";
        const esc = (s) => s
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        let s = esc(src);
        // code blocks ```...```
        s = s.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code}</code></pre>`);
        // inline code
        s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
        // headings
        s = s.replace(/^######\s+(.+)$/gm, "<h4>$1</h4>");
        s = s.replace(/^#####\s+(.+)$/gm, "<h4>$1</h4>");
        s = s.replace(/^####\s+(.+)$/gm, "<h4>$1</h4>");
        s = s.replace(/^###\s+(.+)$/gm, "<h3>$1</h3>");
        s = s.replace(/^##\s+(.+)$/gm, "<h2>$1</h2>");
        s = s.replace(/^#\s+(.+)$/gm, "<h2>$1</h2>");
        // bold / italic
        s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
        // ordered lists
        s = s.replace(/(^|\n)((?:\s*\d+\.\s.+\n?)+)/g, (_, p, block) => {
            const items = block.trim().split(/\n/).map(
                (l) => "<li>" + l.replace(/^\s*\d+\.\s+/, "") + "</li>"
            ).join("");
            return p + "<ol>" + items + "</ol>";
        });
        // unordered lists
        s = s.replace(/(^|\n)((?:\s*[-*]\s.+\n?)+)/g, (_, p, block) => {
            const items = block.trim().split(/\n/).map(
                (l) => "<li>" + l.replace(/^\s*[-*]\s+/, "") + "</li>"
            ).join("");
            return p + "<ul>" + items + "</ul>";
        });
        // paragraphs (blank-line separated)
        s = s.split(/\n{2,}/).map((blk) => {
            if (/^\s*<(h\d|ul|ol|pre|blockquote)/.test(blk)) return blk;
            return "<p>" + blk.replace(/\n/g, "<br/>") + "</p>";
        }).join("\n");
        return s;
    }

    // ---------- rendering ----------
    function render() {
        const tbody = $("#grid-body");
        tbody.innerHTML = "";
        if (!state.rows.length) {
            $("#empty-state").hidden = false;
            return;
        }
        $("#empty-state").hidden = true;
        state.rows.forEach((row, idx) => tbody.appendChild(renderRow(row, idx)));
    }

    function renderRow(row, idx) {
        const tr = el("tr", { "data-id": row.id });

        // #
        tr.appendChild(el("td", { class: "row-index" }, [
            String(idx + 1),
            el("div", { class: "row-actions" }, [
                el("button", {
                    class: "btn ghost small",
                    title: "查看完整详情",
                    onclick: () => openDrawer(row.id),
                }, "详情"),
                el("button", {
                    class: "btn danger small",
                    onclick: () => onDelete(row.id),
                }, "删除"),
            ]),
        ]));

        // ① JD
        tr.appendChild(renderTextareaCell(row, "job_desc", "填写岗位需求 / JD..."));

        // ② 简历
        tr.appendChild(renderResumeCell(row));

        // ③ 关注事项
        tr.appendChild(renderTextareaCell(row, "focus_points", "希望在面试中重点考察的方向..."));

        // ④ 面试问题
        tr.appendChild(renderQuestionsCell(row));

        // ⑤ 面试记录
        tr.appendChild(renderTextareaCell(row, "interview_notes", "粘贴/录入本次面试的对话或纪要..."));

        // ⑥ AI 分析 & 打分
        tr.appendChild(renderAnalysisCell(row));

        return tr;
    }

    function renderTextareaCell(row, field, placeholder) {
        const td = el("td");
        const ta = el("textarea", {
            class: "cell-textarea",
            placeholder,
        });
        ta.value = row[field] || "";
        const save = debounce(async () => {
            try {
                await api.update(row.id, { [field]: ta.value });
                row[field] = ta.value;
            } catch (e) {
                toast("保存失败: " + e.message, "err");
            }
        }, 700);
        ta.addEventListener("input", save);
        td.appendChild(ta);
        return td;
    }

    function renderResumeCell(row) {
        const td = el("td");
        const box = el("div", { class: "resume-box" });

        const status = el("div", { class: "resume-status" });
        if (row.resume_filename) {
            status.appendChild(el("span", { class: "badge-ok" }, "✓ 已解析"));
            status.appendChild(el("span", { class: "filename" }, row.resume_filename));
        } else {
            status.appendChild(el("span", {}, "尚未上传简历"));
        }
        box.appendChild(status);

        const fileLabel = el("label", { class: "btn secondary small" }, [
            row.resume_filename ? "重新上传" : "上传简历",
        ]);
        const input = el("input", {
            type: "file",
            accept: ".pdf,.docx,.txt,.md",
            hidden: "",
        });
        input.addEventListener("change", async () => {
            const file = input.files[0];
            if (!file) return;
            try {
                fileLabel.classList.add("btn-generating");
                const updated = await api.uploadResume(row.id, file);
                Object.assign(row, updated);
                render();
                toast("简历解析成功", "ok");
            } catch (e) {
                toast("上传失败: " + e.message, "err");
            } finally {
                fileLabel.classList.remove("btn-generating");
            }
        });
        fileLabel.appendChild(input);

        const row2 = el("div", { style: "display:flex;gap:6px;flex-wrap:wrap;" }, [fileLabel]);
        if (row.resume_text) {
            row2.appendChild(el("button", {
                class: "btn ghost small",
                onclick: () => openDrawer(row.id, "resume"),
            }, "查看全文"));
        }
        box.appendChild(row2);

        if (row.resume_text) {
            const preview = (row.resume_text || "").slice(0, 400);
            box.appendChild(el("div", { class: "resume-preview" }, preview + (row.resume_text.length > 400 ? "..." : "")));
        }

        td.appendChild(box);
        return td;
    }

    function renderQuestionsCell(row) {
        const td = el("td");
        const box = el("div", { class: "questions-box" });

        const genBtn = el("button", { class: "btn primary small" }, "生成面试问题");
        genBtn.addEventListener("click", async () => {
            genBtn.disabled = true;
            genBtn.classList.add("btn-generating");
            const sp = el("span", { class: "spinner" });
            genBtn.prepend(sp);
            try {
                const updated = await api.genQuestions(row.id);
                Object.assign(row, updated);
                render();
                toast("已生成面试问题", "ok");
            } catch (e) {
                toast("生成失败: " + e.message, "err");
            } finally {
                genBtn.disabled = false;
                genBtn.classList.remove("btn-generating");
            }
        });

        const btnRow = el("div", { style: "display:flex;gap:6px;flex-wrap:wrap;" }, [genBtn]);
        if (row.questions_md) {
            btnRow.appendChild(el("button", {
                class: "btn ghost small",
                onclick: () => openDrawer(row.id, "questions"),
            }, "查看全文"));
            btnRow.appendChild(el("button", {
                class: "btn ghost small",
                onclick: () => copyToClipboard(row.questions_md),
            }, "复制"));
        }
        box.appendChild(btnRow);

        if (row.questions_md) {
            const preview = el("div", { class: "md-preview" });
            preview.innerHTML = renderMarkdown(row.questions_md);
            box.appendChild(preview);
        } else {
            box.appendChild(el("div", { class: "placeholder" },
                "点击「生成面试问题」，AI 将基于 JD + 简历 + 关注事项给出提纲。"));
        }

        td.appendChild(box);
        return td;
    }

    function renderAnalysisCell(row) {
        const td = el("td");
        const box = el("div", { class: "analysis-box" });

        const analyzeBtn = el("button", { class: "btn primary small" }, "AI 分析 + 打分");
        analyzeBtn.addEventListener("click", async () => {
            if (!(row.interview_notes || "").trim()) {
                toast("请先在「面试记录」列填写内容", "err");
                return;
            }
            analyzeBtn.disabled = true;
            analyzeBtn.classList.add("btn-generating");
            analyzeBtn.prepend(el("span", { class: "spinner" }));
            try {
                const updated = await api.analyze(row.id);
                Object.assign(row, updated);
                render();
                toast("已完成面试分析", "ok");
            } catch (e) {
                toast("分析失败: " + e.message, "err");
            } finally {
                analyzeBtn.disabled = false;
                analyzeBtn.classList.remove("btn-generating");
            }
        });

        const btnRow = el("div", { style: "display:flex;gap:6px;flex-wrap:wrap;" }, [analyzeBtn]);
        if (row.analysis) {
            btnRow.appendChild(el("button", {
                class: "btn ghost small",
                onclick: () => openDrawer(row.id, "analysis"),
            }, "查看详情"));
        }
        box.appendChild(btnRow);

        const a = row.analysis;
        if (a && typeof a === "object") {
            const card = el("div", { class: "score-card" });
            const rec = (a.recommendation || "").toLowerCase();
            card.appendChild(el("div", { class: "score-top" }, [
                el("div", { class: "score-big" }, String(a.overall_score ?? "?") + " 分"),
                el("span", { class: "rec " + rec }, a.recommendation_label || a.recommendation || "-"),
            ]));
            if (a.fit_summary) {
                card.appendChild(el("div", { class: "summary-line" }, a.fit_summary));
            }
            box.appendChild(card);

            if (Array.isArray(a.dimensions) && a.dimensions.length) {
                const dimBox = el("div", { class: "dim-grid" });
                a.dimensions.slice(0, 6).forEach((d) => {
                    const score = clampScore(d.score);
                    const row2 = el("div", { class: "dim-row" }, [
                        el("div", {}, [
                            el("div", { class: "dim-name" }, d.name || "维度"),
                            el("div", { class: "bar", style: `--w:${score}%` }),
                        ]),
                        el("div", { class: "dim-score" }, String(score)),
                    ]);
                    dimBox.appendChild(row2);
                });
                box.appendChild(dimBox);
            }
        } else {
            box.appendChild(el("div", { class: "placeholder" },
                "填写面试记录后点击「AI 分析 + 打分」。"));
        }

        td.appendChild(box);
        return td;
    }

    function clampScore(n) {
        const v = Number(n);
        if (!isFinite(v)) return 0;
        return Math.max(0, Math.min(100, Math.round(v)));
    }

    async function copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text || "");
            toast("已复制到剪贴板", "ok");
        } catch (_) {
            toast("复制失败", "err");
        }
    }

    // ---------- drawer ----------
    function openDrawer(rowId, focus) {
        const row = state.rows.find((r) => r.id === rowId);
        if (!row) return;
        $("#drawer").hidden = false;
        $("#drawer-title").textContent = `候选人详情 · ${row.resume_filename || row.id.slice(0, 8)}`;
        const body = $("#drawer-body");
        body.innerHTML = "";

        const sections = [
            { key: "job_desc", title: "① 岗位需求 JD", text: row.job_desc },
            { key: "resume", title: "② 候选人简历（原文）", text: row.resume_text, file: row.resume_filename },
            { key: "focus_points", title: "③ 关注事项", text: row.focus_points },
            { key: "questions", title: "④ AI 生成的面试问题", md: row.questions_md },
            { key: "interview_notes", title: "⑤ 面试记录", text: row.interview_notes },
            { key: "analysis", title: "⑥ AI 分析 & 打分", analysis: row.analysis },
        ];
        sections.forEach((sec) => {
            const h = el("h3", {}, sec.title + (sec.file ? ` — ${sec.file}` : ""));
            body.appendChild(h);
            if (sec.analysis) {
                body.appendChild(renderAnalysisDetail(sec.analysis));
            } else if (sec.md) {
                const d = el("div", { class: "md-preview" });
                d.innerHTML = renderMarkdown(sec.md);
                body.appendChild(d);
            } else if (sec.text) {
                const pre = el("pre", {
                    style: "white-space:pre-wrap;background:#f8fafc;padding:10px;border-radius:6px;font-family:inherit;font-size:12.5px;",
                }, sec.text);
                body.appendChild(pre);
            } else {
                body.appendChild(el("div", { class: "placeholder" }, "（空）"));
            }
        });

        if (focus) {
            const target = body.querySelector(`h3`);
            if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    function renderAnalysisDetail(a) {
        const wrap = el("div");
        const card = el("div", { class: "score-card" });
        const rec = (a.recommendation || "").toLowerCase();
        card.appendChild(el("div", { class: "score-top" }, [
            el("div", { class: "score-big" }, String(a.overall_score ?? "?") + " 分"),
            el("span", { class: "rec " + rec }, a.recommendation_label || a.recommendation || "-"),
        ]));
        if (a.fit_summary) card.appendChild(el("div", { class: "summary-line" }, a.fit_summary));
        wrap.appendChild(card);

        if (Array.isArray(a.dimensions)) {
            wrap.appendChild(el("h4", {}, "评分维度"));
            const list = el("div", { class: "dim-grid" });
            a.dimensions.forEach((d) => {
                const score = clampScore(d.score);
                list.appendChild(el("div", { style: "margin:6px 0;" }, [
                    el("div", { class: "dim-row" }, [
                        el("div", {}, [
                            el("div", { class: "dim-name" }, d.name || "维度"),
                            el("div", { class: "bar", style: `--w:${score}%` }),
                        ]),
                        el("div", { class: "dim-score" }, String(score)),
                    ]),
                    el("div", { class: "summary-line" }, d.comment || ""),
                ]));
            });
            wrap.appendChild(list);
        }

        const pushList = (title, arr) => {
            if (!Array.isArray(arr) || !arr.length) return;
            wrap.appendChild(el("h4", {}, title));
            const ul = el("ul");
            arr.forEach((x) => ul.appendChild(el("li", {}, String(x))));
            wrap.appendChild(ul);
        };
        pushList("优势", a.strengths);
        pushList("不足 / 风险", a.concerns);
        pushList("建议追问的问题", a.follow_up_questions);
        pushList("背景核实事项", a.background_check);

        if (a.feedback_to_interviewer) {
            wrap.appendChild(el("h4", {}, "给面试官的复盘建议"));
            wrap.appendChild(el("div", { class: "summary-line" }, a.feedback_to_interviewer));
        }
        if (a.final_advice) {
            wrap.appendChild(el("h4", {}, "综合建议"));
            wrap.appendChild(el("div", { class: "summary-line" }, a.final_advice));
        }
        return wrap;
    }

    // ---------- actions ----------
    async function onDelete(rowId) {
        if (!confirm("确认删除该候选人行？所有信息将不可恢复。")) return;
        try {
            await api.del(rowId);
            state.rows = state.rows.filter((r) => r.id !== rowId);
            render();
            toast("已删除", "ok");
        } catch (e) {
            toast("删除失败: " + e.message, "err");
        }
    }

    async function onAddRow() {
        try {
            const row = await api.create({});
            state.rows.push(row);
            render();
        } catch (e) {
            toast("新增失败: " + e.message, "err");
        }
    }

    async function onBulkUpload(files) {
        if (!files || !files.length) return;
        const jd = $("#bulk-jd").value;
        const focus = $("#bulk-focus").value;
        const hint = $("#bulk-status");
        hint.textContent = `正在上传 ${files.length} 份简历...`;
        try {
            const res = await api.bulkUpload(files, jd, focus);
            (res.created || []).forEach((row) => state.rows.push(row));
            render();
            const errCount = (res.errors || []).length;
            const okCount = (res.created || []).length;
            hint.textContent = `完成：成功 ${okCount} 份，失败 ${errCount} 份`;
            if (errCount) {
                toast(
                    "部分文件失败：" + res.errors.map((e) => `${e.file}(${e.error})`).join("; "),
                    "err"
                );
            } else {
                toast(`批量导入成功 ${okCount} 份`, "ok");
            }
        } catch (e) {
            hint.textContent = "批量上传失败";
            toast("批量失败: " + e.message, "err");
        }
    }

    async function load() {
        try {
            const data = await api.list();
            state.rows = data.rows || [];
            render();
        } catch (e) {
            toast("加载失败: " + e.message, "err");
        }
    }

    // ---------- wire up ----------
    document.addEventListener("DOMContentLoaded", () => {
        $("#btn-add-row").addEventListener("click", onAddRow);
        $("#btn-refresh").addEventListener("click", load);
        $("#bulk-upload").addEventListener("change", (ev) => {
            onBulkUpload(ev.target.files);
            ev.target.value = "";
        });
        $("#drawer-close").addEventListener("click", () => {
            $("#drawer").hidden = true;
        });

        if (!window.AI_HR_META.api_key_set) {
            toast("尚未设置 AI_HR_API_KEY，AI 生成功能将不可用。请参考 README 配置。", "err");
        }

        load();
    });
})();
