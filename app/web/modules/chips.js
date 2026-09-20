/**
 * Quick Chips & Dynamic Choices Module
 */
import { quickChipsBar, dynamicChoiceChips, dynamicContextChips, messageInput } from './dom.js';

export function extractChoiceOptions(text) {
  if (!text) return [];
  const lines = text.split('\n');
  const choices = [];

  for (const rawLine of lines) {
    const line = rawLine.replace(/[*_`]/g, "").trim();

    // Match choices: "A. xxx", "A) xxx", "- A. xxx", "* A. xxx"
    const letterMatch = line.match(/^[-*•]?\s*([A-Fa-f])[\.\)]\s+(.+)$/);
    if (letterMatch) {
      const key = letterMatch[1].toUpperCase();
      const optionText = letterMatch[2].trim();
      if (!choices.some(c => c.key === key)) {
        choices.push({
          key: key,
          text: optionText,
          label: `${key}. ${optionText}`,
          send: key
        });
      }
      continue;
    }

    // Match True / False or Đúng / Sai
    const tfMatch = line.match(/^[-*•]?\s*(True|False|Đúng|Sai)[\.\:]?\s*(.*)$/i);
    if (tfMatch && !line.includes("?")) {
      const key = tfMatch[1].trim();
      if (!choices.some(c => c.key.toLowerCase() === key.toLowerCase())) {
        choices.push({
          key: key,
          text: tfMatch[2].trim() || key,
          label: key,
          send: key
        });
      }
    }
  }

  return choices.length >= 2 ? choices : [];
}

export function updateQuickChipsVisibility() {
  if (!quickChipsBar) return;
  const hasChips = quickChipsBar.querySelectorAll(".chip").length > 0;
  quickChipsBar.style.display = hasChips ? "flex" : "none";
}

export function updateDynamicChoices(choices) {
  if (!dynamicChoiceChips) return;
  dynamicChoiceChips.innerHTML = "";

  if (!choices || choices.length === 0) {
    updateQuickChipsVisibility();
    return;
  }

  choices.forEach(c => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip chip-choice";
    btn.setAttribute("data-send", c.send);
    btn.innerText = c.key;
    btn.title = `${c.key}: ${c.text}`;
    dynamicChoiceChips.appendChild(btn);
  });

  updateQuickChipsVisibility();
}

export function updateContextChips(lastText, resType = "") {
  if (!dynamicContextChips) return;
  dynamicContextChips.innerHTML = "";

  if (!lastText && !resType) {
    if (messageInput) messageInput.placeholder = "Nhập từ cần học...";
    updateQuickChipsVisibility();
    return;
  }

  // Kiem tra neu dang trong mot cau hoi luyen tap
  const isQuestion = resType === "test_question" || (/Câu\s+\d+\/\d+|\[D[1-3]\]|_{2,}/i.test(lastText) && !/Hoàn thành \d+\/\d+ câu/i.test(lastText));
  if (isQuestion) {
    if (messageInput) messageInput.placeholder = "Nhập đáp án (A, B, C, D hoặc từ điền)...";

    // Hint chip for fill-in-the-blank questions
    const hasChoices = dynamicChoiceChips && dynamicChoiceChips.querySelectorAll(".chip-choice").length > 0;
    if (!hasChoices) {
      const hintChip = document.createElement("button");
      hintChip.type = "button";
      hintChip.className = "chip chip-hint";
      hintChip.setAttribute("data-send", "Gợi ý cho tôi chữ cái đầu");
      hintChip.innerText = "💡 Gợi ý";
      hintChip.title = "Bấm để AI gợi ý chữ cái đầu và số ký tự của từ";
      dynamicContextChips.appendChild(hintChip);
    }

    updateQuickChipsVisibility();
    return;
  }

  // Kiem tra neu vua hoan thanh vong luyen tap
  const isCompleted = resType === "round_completed" || /Hoàn thành \d+\/\d+ câu/i.test(lastText);
  if (isCompleted) {
    if (messageInput) messageInput.placeholder = "Nhập số câu luyện tiếp hoặc từ mới...";
    const chip3 = document.createElement("button");
    chip3.type = "button";
    chip3.className = "chip";
    chip3.setAttribute("data-send", "3");
    chip3.innerText = "Luyện tiếp 3 câu";
    dynamicContextChips.appendChild(chip3);

    const chip5 = document.createElement("button");
    chip5.type = "button";
    chip5.className = "chip";
    chip5.setAttribute("data-send", "5");
    chip5.innerText = "Luyện tiếp 5 câu";
    dynamicContextChips.appendChild(chip5);

    updateQuickChipsVisibility();
    return;
  }

  // Kiem tra neu AI vua giai nghia xong tu vung
  const hasNextTestPrompt = resType === "word_explanation" || /\[NEXT\]\s*Nhập số câu|số câu để luyện/i.test(lastText);
  if (hasNextTestPrompt) {
    if (messageInput) messageInput.placeholder = "Nhập số câu cần luyện hoặc yêu cầu khác...";
    const chip3 = document.createElement("button");
    chip3.type = "button";
    chip3.className = "chip";
    chip3.setAttribute("data-send", "3");
    chip3.innerText = "Luyện 3 câu";
    dynamicContextChips.appendChild(chip3);

    const chip5 = document.createElement("button");
    chip5.type = "button";
    chip5.className = "chip";
    chip5.setAttribute("data-send", "5");
    chip5.innerText = "Luyện 5 câu";
    dynamicContextChips.appendChild(chip5);

    const chip10 = document.createElement("button");
    chip10.type = "button";
    chip10.className = "chip";
    chip10.setAttribute("data-send", "10");
    chip10.innerText = "Luyện 10 câu";
    dynamicContextChips.appendChild(chip10);

    updateQuickChipsVisibility();
    return;
  }

  if (messageInput) messageInput.placeholder = "Nhập từ cần học...";
  updateQuickChipsVisibility();
}
