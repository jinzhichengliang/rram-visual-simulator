/**
 * Explanation View Component — Displays state-driven explanations.
 *
 * Shows four explanation cards:
 * 1. Voltage Card — What voltage is applied?
 * 2. Current Card — Where does current flow?
 * 3. Physics Card — Why does the device change (or not)?
 * 4. Sense Card — How do we know the operation succeeded?
 *
 * This component ONLY renders data from the selector.
 * All explanations are generated from FrameState, not hardcoded.
 */
import React from "react";
import type { ExplanationCards } from "../selectors/explanationSelector";

interface ExplanationViewProps {
  cards: ExplanationCards;
}

export const ExplanationView: React.FC<ExplanationViewProps> = ({ cards }) => {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
      {/* Voltage Card */}
      <div style={{ background: "#0f1117", border: "1px solid #2e3348", borderRadius: "8px", padding: "12px" }}>
        <div style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "1px", color: "#6c8cff", marginBottom: "8px" }}>
          ① 施加了什么电压？
        </div>
        <div style={{ fontSize: "12px", lineHeight: "1.6", color: "#e1e4ed" }} dangerouslySetInnerHTML={{ __html: cards.voltage }} />
      </div>

      {/* Current Card */}
      <div style={{ background: "#0f1117", border: "1px solid #2e3348", borderRadius: "8px", padding: "12px" }}>
        <div style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "1px", color: "#6c8cff", marginBottom: "8px" }}>
          ② 电流从哪里流？
        </div>
        <div style={{ fontSize: "12px", lineHeight: "1.6", color: "#e1e4ed" }} dangerouslySetInnerHTML={{ __html: cards.current }} />
      </div>

      {/* Physics Card */}
      <div style={{ background: "#0f1117", border: "1px solid #2e3348", borderRadius: "8px", padding: "12px" }}>
        <div style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "1px", color: "#6c8cff", marginBottom: "8px" }}>
          ③ 器件内部为什么变化？
        </div>
        <div style={{ fontSize: "12px", lineHeight: "1.6", color: "#e1e4ed" }} dangerouslySetInnerHTML={{ __html: cards.physics }} />
      </div>

      {/* Sense Card */}
      <div style={{ background: "#0f1117", border: "1px solid #2e3348", borderRadius: "8px", padding: "12px" }}>
        <div style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "1px", color: "#6c8cff", marginBottom: "8px" }}>
          ④ 系统如何知道操作成功？
        </div>
        <div style={{ fontSize: "12px", lineHeight: "1.6", color: "#e1e4ed" }} dangerouslySetInnerHTML={{ __html: cards.sense }} />
      </div>
    </div>
  );
};
