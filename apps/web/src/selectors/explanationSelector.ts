/**
 * Explanation Engine Selector — Generate state-driven explanations.
 *
 * This selector reads from FrameState and generates human-readable explanations
 * for the three/four key questions:
 * 1. What voltage is applied?
 * 2. Where does current flow?
 * 3. Why does the device change (or not)?
 * 4. How do we know the operation succeeded?
 *
 * CRITICAL: All explanations are derived from ACTUAL state data.
 * The selector compares current frame with previous frame to detect
 * real state transitions, never guesses from operation type alone.
 */
import type { FrameState } from "../../../../packages/contracts/types";

export interface ExplanationCards {
  voltage: string;
  current: string;
  physics: string;
  sense: string;
}

/**
 * Generate explanation cards from FrameState.
 *
 * @param frame - Current FrameState
 * @param prevFrame - Previous FrameState (null for first frame)
 *
 * Pure function — explanations are derived from actual state diffs, not hardcoded.
 */
export function selectExplanation(
  frame: FrameState,
  prevFrame: FrameState | null = null
): ExplanationCards {
  const { operation, phase, cell, nodes, selectedCell, sense } = frame;

  const row = selectedCell?.row ?? 0;
  const col = selectedCell?.col ?? 0;

  const wlV = nodes.wl[row] || 0;
  const blV = nodes.bl[col] || 0;
  const slV = nodes.sl[col] || 0;
  const vRram = cell.rram.v;
  const iRram = cell.rram.i;
  const state = cell.rram.state;
  const formingDone = cell.rram.formingDone;
  const transistorOn = cell.transistor.on;

  // ── Compute actual state diff ──────────────────────────────────
  const prevState = prevFrame?.cell.rram.state ?? null;
  const prevFormingDone = prevFrame?.cell.rram.formingDone ?? false;
  const stateJustChanged = prevState !== null && prevState !== state;
  const formingJustCompleted = !prevFormingDone && formingDone;

  // ══════════════════════════════════════════════════════════════
  // Question 1: What voltage is applied?
  // ══════════════════════════════════════════════════════════════
  let voltage = "";
  if (phase === "PREPARE" || phase === "RELEASE" || phase === "COMPLETE") {
    voltage = `WL=0V, BL=0V, SL=0V — 无有效偏置，器件两端 V_RRAM = 0V。`;
  } else {
    const polarityDesc =
      vRram > 0.001 ? "正向（BL > SL）" : vRram < -0.001 ? "反向（BL < SL）" : "零";
    voltage = `WL=${wlV.toFixed(1)}V，BL=${blV.toFixed(1)}V，SL=${slV.toFixed(1)}V。`;
    voltage += ` V_RRAM = ${vRram.toFixed(2)}V，极性：${polarityDesc}。`;

    if (operation === "FORMING") {
      voltage += ` 当前为 Forming 操作，电压高于正常 SET/RESET。`;
    } else if (operation === "READ") {
      voltage += ` 当前为 Read 操作，电压低于写入阈值。`;
    } else if (operation === "SET") {
      voltage += ` 当前为 SET（写 1）操作。`;
    } else if (operation === "RESET") {
      voltage += ` 当前为 RESET（写 0）操作。`;
    }
  }

  // ══════════════════════════════════════════════════════════════
  // Question 2: Where does current flow?
  // ══════════════════════════════════════════════════════════════
  let current = "";
  if (!transistorOn) {
    current = `NMOS 截止（Vgs < Vth），无有效电流路径。I_RRAM ≈ 0。`;
  } else if (Math.abs(iRram) < 0.01) {
    current = `NMOS 导通，但 V_RRAM ≈ 0，电流极小（${iRram.toFixed(2)} µA）。`;
  } else {
    const direction = iRram > 0 ? "BL → RRAM → NMOS → SL" : "SL → NMOS → RRAM → BL";
    current = `电流路径：${direction}。I_RRAM = ${iRram.toFixed(1)} µA。`;

    // Check compliance from frame checks
    const complianceCheck = frame.checks.find((c) => c.ruleId === "INV-004");
    if (complianceCheck && !complianceCheck.passed) {
      current += ` ⚡ Compliance 限流已介入。`;
    }
  }

  // ══════════════════════════════════════════════════════════════
  // Question 3: Why does the device change (or not)?
  // ══════════════════════════════════════════════════════════════
  let physics = "";

  if (phase === "PREPARE" || phase === "RELEASE" || phase === "COMPLETE") {
    // No bias phase
    physics = `无有效偏置，器件状态保持（${state}）。`;
  } else if (phase === "BIAS_RAMP") {
    // Bias is being applied but no state change yet
    physics = `偏置已施加，正在建立电场。当前状态仍为 ${state}。`;
  } else if (stateJustChanged) {
    // ── ACTUAL state transition detected ──
    if (prevState === "PRISTINE" && state === "LRS") {
      physics = `Forming 完成！首次建立导电通路。缺陷/离子重新分布，导电细丝形成。`;
      physics += ` 状态：PRISTINE → LRS。`;
    } else if (prevState === "HRS" && state === "LRS") {
      physics = `V_RRAM = ${vRram.toFixed(2)}V 满足 SET 条件，导电细丝重新接通，gap 缩小。`;
      physics += ` 状态：HRS → LRS。`;
    } else if (prevState === "LRS" && state === "HRS") {
      physics = `V_RRAM = ${vRram.toFixed(2)}V 满足 RESET 条件，导电细丝断裂，gap 增大。`;
      physics += ` 状态：LRS → HRS。`;
    } else {
      physics = `状态发生变化：${prevState} → ${state}。`;
    }
  } else if (operation === "READ" && transistorOn && Math.abs(iRram) >= 0.01) {
    // READ with measurable current but no state change
    physics = `V_RRAM = ${vRram.toFixed(2)}V，低于写入阈值。`;
    physics += `产生读电流 ${iRram.toFixed(2)} µA 用于感测，但电场不足以引起状态转移。`;
    physics += ` 器件状态保持（${state}）——这就是非破坏性读取。`;
  } else if (operation === "READ" && transistorOn) {
    // READ with very small current
    physics = `V_RRAM = ${vRram.toFixed(2)}V，低于写入阈值。`;
    physics += `读电流极小（${iRram.toFixed(2)} µA），器件状态保持（${state}）——非破坏性读取。`;
  } else if (transistorOn && !stateJustChanged) {
    // Bias applied, transistor ON, but no state change
    physics = `V_RRAM = ${vRram.toFixed(2)}V，I_RRAM = ${iRram.toFixed(1)} µA。`;
    if (operation === "FORMING" && state === "PRISTINE") {
      physics += ` 电压尚未达到 forming 阈值，导电通路尚未建立。`;
    } else if (operation === "SET" && state === "HRS") {
      physics += ` 电压尚未达到 SET 阈值，细丝尚未接通。`;
    } else if (operation === "RESET" && state === "LRS") {
      physics += ` 电压尚未达到 RESET 阈值，细丝尚未断裂。`;
    } else {
      physics += ` 当前条件不足以引起状态转移，器件保持 ${state}。`;
    }
  } else if (!transistorOn) {
    physics = `NMOS 截止，无电流路径，器件状态保持（${state}）。`;
  } else {
    physics = `当前状态：${state}。V_RRAM = ${vRram.toFixed(2)}V。`;
  }

  // ══════════════════════════════════════════════════════════════
  // Question 4: How do we know the operation succeeded?
  // ══════════════════════════════════════════════════════════════
  let senseText = "";
  if (sense) {
    senseText = `I_read = ${sense.currentUa.toFixed(2)} µA，I_ref = ${sense.referenceUa.toFixed(2)} µA。`;
    senseText += ` Margin = ${sense.marginUa?.toFixed(2) ?? "N/A"} µA。`;
    senseText += ` 判定：${sense.decision}（逻辑 ${sense.decision === "LRS" ? "1" : "0"}）。`;
  } else if (operation === "READ" && (phase === "ACTIVE" || phase === "BIAS_RAMP")) {
    senseText = `当前为 ${phase} 阶段，尚未进入 SENSE。下一步将采样读电流并与参考值比较。`;
  } else if (operation !== "READ") {
    senseText = `当前操作为 ${operation}，不执行 Sense 判决。`;
  } else {
    senseText = `等待 SENSE 阶段…`;
  }

  return { voltage, current, physics, sense: senseText };
}
