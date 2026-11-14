"use strict";
const copy = document.querySelector("[data-copy]");
copy?.addEventListener("click", async () => {
  const input = document.getElementById(copy.dataset.copy);
  try {
    await navigator.clipboard.writeText(input.value);
    document.getElementById("copy-status").textContent = "Link copied.";
  } catch {
    input.select();
    document.getElementById("copy-status").textContent =
      "Select and copy the link above.";
  }
});
document
  .querySelector("[data-print]")
  ?.addEventListener("click", () => window.print());
const form = document.getElementById("builder");
if (form) {
  const survey = JSON.parse(document.getElementById("survey-data").textContent),
    list = document.getElementById("questions"),
    status = document.getElementById("save-status"),
    save = document.getElementById("save-survey");
  let questions = survey.questions,
    revision = survey.revision,
    dirty = false,
    pending = 0;
  const mark = () => {
    dirty = true;
    status.textContent = "Unsaved changes";
  };
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const button = (label, action) => {
    const b = el("button", "outline small", label);
    b.type = "button";
    b.addEventListener("click", action);
    return b;
  };
  function field(label, value, change, type = "text") {
    const wrap = el("label", "", label),
      input = el("input");
    input.type = type;
    input.value = value;
    input.addEventListener("input", () => {
      change(input.value);
      mark();
    });
    wrap.append(input);
    return wrap;
  }
  function render() {
    list.replaceChildren();
    questions.forEach((q, index) => {
      const section = el("section", "panel question-editor"),
        top = el("div", "heading"),
        actions = el("div", "actions");
      top.append(el("h2", "", `Question ${index + 1}`));
      const move = (direction) => {
        const next = index + direction;
        if (next < 0 || next >= questions.length) return;
        [questions[index], questions[next]] = [
          questions[next],
          questions[index],
        ];
        mark();
        render();
      };
      const up = button("Move up", () => move(-1)),
        down = button("Move down", () => move(1));
      up.disabled = index === 0;
      down.disabled = index === questions.length - 1;
      actions.append(
        up,
        down,
        button("Remove", () => {
          questions.splice(index, 1);
          mark();
          render();
        }),
      );
      top.append(actions);
      section.append(top);
      const title = field("Question", q.label, (v) => (q.label = v));
      title.querySelector("input").maxLength = 300;
      title.querySelector("input").required = true;
      section.append(title);
      const typeLabel = el("label", "", "Answer type"),
        type = el("select");
      for (const [value, name] of Object.entries({
        single: "Choose one",
        multiple: "Choose several",
        rating: "Rating (1–5)",
        text: "Written answer",
      })) {
        const option = el("option", "", name);
        option.value = value;
        option.selected = q.kind === value;
        type.append(option);
      }
      type.addEventListener("change", () => {
        q.kind = type.value;
        if (["single", "multiple"].includes(q.kind) && q.options.length < 2)
          q.options = [
            { label: "", color: "" },
            { label: "", color: "" },
          ];
        mark();
        render();
      });
      typeLabel.append(type);
      section.append(typeLabel);
      const required = el("label", "check"),
        check = el("input");
      check.type = "checkbox";
      check.checked = q.required;
      check.addEventListener("change", () => {
        q.required = check.checked;
        mark();
      });
      required.append(check, el("span", "", "Required answer"));
      section.append(required);
      if (q.photo) {
        const image = el("img", "builder-photo");
        image.src = form.dataset.photoBase + encodeURIComponent(q.photo);
        image.alt = q.alt || "Uploaded product photo";
        section.append(
          image,
          button("Remove photo", () => {
            q.photo = "";
            q.alt = "";
            mark();
            render();
          }),
        );
      }
      const photoLabel = el("label", "", "Product photo"),
        file = el("input");
      file.type = "file";
      file.accept = "image/jpeg,image/png,image/webp";
      file.addEventListener("change", async () => {
        if (!file.files[0]) return;
        const body = new FormData();
        body.append("photo", file.files[0]);
        body.append("csrf", form.elements.csrf.value);
        pending++;
        save.disabled = true;
        file.disabled = true;
        status.textContent = "Uploading photo…";
        try {
          const response = await fetch(form.dataset.upload, {
            method: "POST",
            body,
          });
          const data = await response.json();
          if (!response.ok) throw new Error(data.error || "Upload failed.");
          q.photo = data.id;
          mark();
          render();
        } catch (error) {
          status.textContent = error.message;
        } finally {
          pending--;
          save.disabled = pending > 0;
          file.disabled = false;
        }
      });
      photoLabel.append(file);
      section.append(photoLabel);
      if (q.photo) {
        const alt = field("Photo description", q.alt || "", (v) => (q.alt = v));
        alt.querySelector("input").required = true;
        alt.querySelector("input").maxLength = 300;
        section.append(alt);
      }
      if (["single", "multiple"].includes(q.kind)) {
        const options = el("div", "option-editor");
        options.append(el("h3", "", "Answer options"));
        q.options.forEach((option, oi) => {
          const row = el("div", "option-row"),
            label = field(
              `Option ${oi + 1}`,
              option.label,
              (v) => (option.label = v),
            );
          label.querySelector("input").required = true;
          label.querySelector("input").maxLength = 100;
          const color = field(
            "Color swatch",
            option.color || "#81f268",
            (v) => (option.color = v),
            "color",
          );
          row.append(
            label,
            color,
            button(option.color ? "Clear swatch" : "No swatch", () => {
              option.color = "";
              mark();
              render();
            }),
            button("Remove option", () => {
              q.options.splice(oi, 1);
              mark();
              render();
            }),
          );
          options.append(row);
        });
        const add = button("+ Add option", () => {
          q.options.push({ label: "", color: "" });
          mark();
          render();
        });
        add.disabled = q.options.length >= 20;
        options.append(add);
        section.append(options);
      }
      list.append(section);
    });
    document
      .querySelectorAll("[data-add]")
      .forEach((b) => (b.disabled = questions.length >= 20));
  }
  document.querySelectorAll("[data-add]").forEach((b) =>
    b.addEventListener("click", () => {
      if (questions.length >= 20) return;
      const colors = b.dataset.add === "colors";
      questions.push({
        id: crypto.randomUUID(),
        label: colors
          ? "Which colors would you like to see this product in?"
          : "",
        kind: colors ? "multiple" : b.dataset.add,
        required: true,
        photo: "",
        alt: "",
        options: colors
          ? [
              { label: "Green", color: "#81f268" },
              { label: "Teal", color: "#25b8b0" },
              { label: "Lilac", color: "#b9a3ed" },
              { label: "Black", color: "#151515" },
            ]
          : [
              { label: "", color: "" },
              { label: "", color: "" },
            ],
      });
      mark();
      render();
      list.lastElementChild.scrollIntoView({
        behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
        block: "start",
      });
    }),
  );
  form.addEventListener("input", mark);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (pending) return;
    save.disabled = true;
    status.textContent = "Saving…";
    try {
      const response = await fetch(form.dataset.save, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": form.elements.csrf.value,
        },
        body: JSON.stringify({
          title: form.elements.title.value,
          description: form.elements.description.value,
          thank_you: form.elements.thank_you.value,
          revision,
          questions,
        }),
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(
          data.error || "Could not save. Sign in again and retry.",
        );
      revision = data.revision;
      dirty = false;
      status.textContent =
        "Draft saved. Preview it, then publish from the survey overview.";
    } catch (error) {
      status.textContent = error.message;
    } finally {
      save.disabled = false;
    }
  });
  window.addEventListener("beforeunload", (e) => {
    if (dirty || pending) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
  render();
}
