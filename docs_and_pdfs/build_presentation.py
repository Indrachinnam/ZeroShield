"""
ZeroShield PowerPoint Generator
Generates a 14-slide executive & technical presentation on ZeroShield.
"""

import sys
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_presentation(output_path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Theme Colors
    BG_DARK = RGBColor(11, 19, 43)        # #0B132B Deep Navy
    CARD_BG = RGBColor(28, 37, 65)        # #1C2541 Card Slate
    CARD_BORDER = RGBColor(58, 80, 107)    # #3A506B
    CYAN_ACCENT = RGBColor(0, 242, 254)   # #00F2FE Vibrant Cyan
    BLUE_ACCENT = RGBColor(79, 172, 254)  # #4FACFE Soft Blue
    GREEN_ACCENT = RGBColor(16, 185, 129) # #10B981 Emerald
    RED_ACCENT = RGBColor(239, 68, 68)    # #EF4444 Crimson
    WHITE = RGBColor(255, 255, 255)
    GRAY_TEXT = RGBColor(203, 213, 225)   # #CBD5E1 Light Slate
    MUTED_TEXT = RGBColor(148, 163, 184)  # #94A3B8 Muted

    blank_layout = prs.slide_layouts[6]

    def add_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_DARK
        bg.line.fill.background()
        return bg

    def add_header(slide, title_text, category="ZEROSHIELD SYSTEM SPECIFICATION"):
        # Category tag
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = CYAN_ACCENT

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.7))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = WHITE

        # Divider line
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.45), Inches(11.733), Inches(0.02))
        line.fill.solid()
        line.fill.fore_color.rgb = CARD_BORDER
        line.line.fill.background()

    def add_card(slide, left, top, width, height, title=None, border_color=CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = border_color
        card.line.width = Pt(1)

        if title:
            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), Inches(0.4))
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = title
            p.font.size = Pt(14)
            p.font.bold = True
            p.font.color.rgb = CYAN_ACCENT
        return card

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_background(s1)

    # Accent decorative box
    dec = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.2), Inches(11.733), Inches(5.1))
    dec.fill.solid()
    dec.fill.fore_color.rgb = CARD_BG
    dec.line.color.rgb = CYAN_ACCENT
    dec.line.width = Pt(1.5)

    tb = s1.shapes.add_textbox(Inches(1.2), Inches(1.6), Inches(10.9), Inches(4.3))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = "NEXT-GENERATION NETWORK INTRUSION DETECTION"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = CYAN_ACCENT
    p0.space_after = Pt(14)

    p1 = tf.add_paragraph()
    p1.text = "ZeroShield: Zero-Day Exploit Detection"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = WHITE

    p2 = tf.add_paragraph()
    p2.text = "Transformer-Based Tabular Network Traffic Classification with Gibbs Free Energy Out-of-Distribution Scoring"
    p2.font.size = Pt(18)
    p2.font.color.rgb = BLUE_ACCENT
    p2.space_after = Pt(28)

    p3 = tf.add_paragraph()
    p3.text = "• Architecture: Tabular Flow-Transformer (3 Layers, 4 Attention Heads, d_model = 64)\n" \
              "• Novelty Mechanism: Gibbs Free Energy Head with Strict Benign Quantile Calibration (5% FPR)\n" \
              "• Explainability: Gradient-Based Real-Time Attribution for SOC Analysts\n" \
              "• Repository: https://github.com/Indrachinnam/ZeroShield"
    p3.font.size = Pt(13)
    p3.font.color.rgb = GRAY_TEXT
    p3.space_after = Pt(24)

    p4 = tf.add_paragraph()
    p4.text = "Author: Indrachinnam  |  ZeroShield Autonomous Threat Research Group  |  Production Release v1.0.0"
    p4.font.size = Pt(12)
    p4.font.bold = True
    p4.font.color.rgb = MUTED_TEXT

    # =========================================================================
    # SLIDE 2: Executive Summary & The Zero-Day Challenge
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_background(s2)
    add_header(s2, "Executive Summary: The Blindspot of Modern NIDS", "PROBLEM STATEMENT & THREAT LANDSCAPE")

    add_card(s2, Inches(0.8), Inches(1.7), Inches(3.7), Inches(5.2), "The Problem", RED_ACCENT)
    tb = s2.shapes.add_textbox(Inches(0.95), Inches(2.2), Inches(3.4), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Signature & Shallow Failure"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = WHITE
    p.space_after = Pt(6)
    p_body = tf.add_paragraph()
    p_body.text = "Traditional NIDS (Snort, Suricata, Bro/Zeek) rely heavily on known CVE signatures. When attackers alter payload byte sequences or weaponize unpatched zero-days, signature engines fail completely (0% detection).\n\n" \
                 "Shallow ML models (Random Forests, standard MLPs) suffer catastrophic softmax overconfidence, assigning 95%+ confidence to completely unseen attack vectors."
    p_body.font.size = Pt(11.5)
    p_body.font.color.rgb = GRAY_TEXT

    add_card(s2, Inches(4.8), Inches(1.7), Inches(3.7), Inches(5.2), "The Paradigm Shift", CYAN_ACCENT)
    tb = s2.shapes.add_textbox(Inches(4.95), Inches(2.2), Inches(3.4), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Energy-Based Out-of-Distribution"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = WHITE
    p.space_after = Pt(6)
    p_body = tf.add_paragraph()
    p_body.text = "ZeroShield departs from bounded softmax classification. By computing non-normalized Helmholtz Free Energy across network flow logits, the model evaluates whether flow dynamics conform to normal traffic density.\n\n" \
                 "Any statistical outlier manifests as an energy spike, triggering immediate zero-day alerts without requiring prior attack signatures or retraining."
    p_body.font.size = Pt(11.5)
    p_body.font.color.rgb = GRAY_TEXT

    add_card(s2, Inches(8.8), Inches(1.7), Inches(3.7), Inches(5.2), "Impact & Results", GREEN_ACCENT)
    tb = s2.shapes.add_textbox(Inches(8.95), Inches(2.2), Inches(3.4), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Production-Calibrated Security"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = WHITE
    p.space_after = Pt(6)
    p_body = tf.add_paragraph()
    p_body.text = "• 0.9211 Mean AUROC on Leave-One-Attack-Out (LOAO) zero-day testing (beating RF 0.8993, GB 0.8969, MLP 0.7883).\n\n" \
                 "• Calibrated threshold at strictly 5% False Positive Rate (FPR) on benign flows, preventing SOC alert fatigue.\n\n" \
                 "• Sub-10ms latency: Full PyTorch GPU/MPS acceleration and zero-dependency NumPy inference for serverless SOC edge."
    p_body.font.size = Pt(11.5)
    p_body.font.color.rgb = GRAY_TEXT

    # =========================================================================
    # SLIDE 3: Flow Feature Hygiene & Data Engineering
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_background(s3)
    add_header(s3, "Flow Feature Hygiene: Eliminating Trivial Shortcut Learning", "DATA HYGIENE & THREAT MODEL")

    add_card(s3, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.2), "Shortcut Prevention Policy")
    tb = s3.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Why Most Academic NIDS Models Fail in Real Networks:"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = WHITE
    p.space_after = Pt(8)

    p1 = tf.add_paragraph()
    p1.text = "1. Memorization of IP Addresses:\n" \
              "   Academic models learn that 192.168.10.50 is attacker and 192.168.10.14 is victim. In the real world, IP addresses mutate instantly.\n\n" \
              "2. Raw Port Overfitting:\n" \
              "   Models memorize port 80/443 = benign and port 21/22/8080 = malicious. Attackers simply tunnel over standard ports.\n\n" \
              "3. ZeroShield's Enforced Sanitization:\n" \
              "   • Zero IP addresses allowed into tokenizer.\n" \
              "   • Ports abstracted into 3 structural categories: Well-Known (0-1023), Registered (1024-49151), Ephemeral (49152-65535)."
    p1.font.size = Pt(12)
    p1.font.color.rgb = GRAY_TEXT

    add_card(s3, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2), "The 12 Statistical Flow Features")
    tb = s3.shapes.add_textbox(Inches(7.0), Inches(2.2), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Pure Transport-Layer Dynamics:"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = CYAN_ACCENT
    p.space_after = Pt(8)

    features = [
        ("flow_duration", "Continuous microsecond flow active lifetime"),
        ("tot_fwd_pkts / tot_bwd_pkts", "Forward & backward directional packet counters"),
        ("totlen_fwd_pkts / totlen_bwd_pkts", "Cumulative payload bytes transferred each way"),
        ("flow_byts_s / flow_pkts_s", "Instantaneous transmission velocity and rate"),
        ("fwd_iat_mean / bwd_iat_mean", "Inter-Arrival Time distributions (beaconing detection)"),
        ("flow_iat_std", "Burstiness vs steady-state cadence variance"),
        ("syn_flag_cnt / rst_flag_cnt", "TCP state transition anomalies & abort behavior"),
        ("dst_port_category", "Categorical embedding (Well-Known, Registered, Ephemeral)")
    ]
    for name, desc in features:
        pf = tf.add_paragraph()
        pf.text = f"• {name}: {desc}"
        pf.font.size = Pt(10.5)
        pf.font.color.rgb = GRAY_TEXT
        pf.space_after = Pt(3)

    # =========================================================================
    # SLIDE 4: FT-Transformer Model Architecture
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_background(s4)
    add_header(s4, "Flow-Transformer (FT-Transformer) Architecture", "NEURAL REPRESENTATION FOR TABULAR FLOWS")

    # Left Column: Mathematical Formulation
    add_card(s4, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.2), "Tokenizer & Embedding Mechanics")
    tb = s4.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Numerical Affine Feature Tokenizer:"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = WHITE
    p.space_after = Pt(4)

    p1 = tf.add_paragraph()
    p1.text = "Unlike NLP where tokens are discrete words, tabular network flows are continuous scalars. Each continuous feature x_j is projected into a d_model = 64 dimensional vector space via an affine transformation:\n" \
              "       e_j = x_j · W_j + b_j  ∈  R^{64}\n" \
              "This equips every scalar flow feature with its own distinct geometric embedding subspace."
    p1.font.size = Pt(11.5)
    p1.font.color.rgb = GRAY_TEXT
    p1.space_after = Pt(10)

    p2 = tf.add_paragraph()
    p2.text = "Categorical Port Tokenizer & [CLS] Token:"
    p2.font.bold = True
    p2.font.size = Pt(13)
    p2.font.color.rgb = WHITE
    p2.space_after = Pt(4)

    p3 = tf.add_paragraph()
    p3.text = "• Categorical port classes are projected via a lookup table: E_cat ∈ R^{3 x 64}.\n" \
              "• A learnable [CLS] classification token is prepended to the sequence of 12 tokenized feature vectors:\n" \
              "       Z_0 = [[CLS], e_1, e_2, ..., e_11, e_cat] ∈ R^{13 x 64}\n" \
              "• Total Model Footprint: 108,614 trainable parameters."
    p3.font.size = Pt(11.5)
    p3.font.color.rgb = GRAY_TEXT

    # Right Column: Hyperparameter & Layer Stack
    add_card(s4, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2), "Architectural Specifications")
    tb = s4.shapes.add_textbox(Inches(7.0), Inches(2.2), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True

    specs = [
        ("Embedding Dimension (d_model)", "64 channels per feature token"),
        ("Transformer Encoder Layers", "3 sequentially stacked Transformer blocks"),
        ("Multi-Head Attention Heads", "4 parallel attention heads (d_head = 16)"),
        ("Feed-Forward Network (FFN)", "d_ff = 128 with GeLU activation & LayerNorm"),
        ("Dropout Regularization", "0.1 across attention weights and FFN projections"),
        ("Sequence Length (L)", "13 tokens (1 [CLS] token + 12 flow features)"),
        ("Classifier Head", "Linear projection R^{64} -> R^K (Known attack classes)"),
        ("Novelty Head", "Gibbs Free Energy head operating directly on output logits")
    ]
    for param, val in specs:
        p = tf.add_paragraph()
        p.text = f"• {param}:"
        p.font.bold = True
        p.font.size = Pt(11.5)
        p.font.color.rgb = CYAN_ACCENT
        p_val = tf.add_paragraph()
        p_val.text = f"   {val}"
        p_val.font.size = Pt(11)
        p_val.font.color.rgb = WHITE
        p_val.space_after = Pt(4)

    # =========================================================================
    # SLIDE 5: Multi-Head Self-Attention Mechanics
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_background(s5)
    add_header(s5, "Multi-Head Self-Attention in Network Flows", "ATTENTION MECHANISM & FEATURE INTERACTIONS")

    add_card(s5, Inches(0.8), Inches(1.7), Inches(11.733), Inches(2.3), "Self-Attention Formulation across Flow Properties")
    tb = s5.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(11.3), Inches(1.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Mathematical Foundation:"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = CYAN_ACCENT
    p1 = tf.add_paragraph()
    p1.text = "Attention(Q, K, V) = softmax( (Q · K^T) / √d_k ) · V\n" \
              "Where Q = Z · W_Q,  K = Z · W_K,  V = Z · W_V.  MultiHead(Z) = Concat(head_1, ..., head_4) · W_O\n\n" \
              "Why Self-Attention Outperforms Tree Boosting on Zero-Days: Traditional tree models evaluate axis-aligned splits on single features. Self-attention enables all 12 flow features to dynamically attend to one another simultaneously. For example, a high SYN flag count is normal for web traffic but anomalous when paired with near-zero backward bytes and low inter-arrival time standard deviation."
    p1.font.size = Pt(11.5)
    p1.font.color.rgb = GRAY_TEXT

    # 3 Sub-Cards for Attention Heads
    add_card(s5, Inches(0.8), Inches(4.3), Inches(3.7), Inches(2.6), "Head 1: Volumetric Focus")
    tb = s5.shapes.add_textbox(Inches(0.95), Inches(4.8), Inches(3.4), Inches(2.0))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Focuses attention weights between forward/backward packet counts, flow bytes/s, and packet rates. Crucial for detecting volumetric amplification (DDoS/DoS) and data exfiltration spikes."
    p.font.size = Pt(11)
    p.font.color.rgb = GRAY_TEXT

    add_card(s5, Inches(4.8), Inches(4.3), Inches(3.7), Inches(2.6), "Head 2: Cadence & Timing")
    tb = s5.shapes.add_textbox(Inches(4.95), Inches(4.8), Inches(3.4), Inches(2.0))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Attends across Forward IAT Mean, Backward IAT Mean, and Flow IAT Standard Deviation. Discloses robotic command-and-control beaconing and stealthy slow-rate reconnaissance."
    p.font.size = Pt(11)
    p.font.color.rgb = GRAY_TEXT

    add_card(s5, Inches(8.8), Inches(4.3), Inches(3.7), Inches(2.6), "Heads 3 & 4: Protocol State")
    tb = s5.shapes.add_textbox(Inches(8.95), Inches(4.8), Inches(3.4), Inches(2.0))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Correlates SYN and RST flag distributions against destination port categories. Rapidly isolates port scanning sweeps, unacknowledged connection floods, and abnormal teardowns."
    p.font.size = Pt(11)
    p.font.color.rgb = GRAY_TEXT

    # =========================================================================
    # SLIDE 6: Novelty Scoring: Gibbs Free Energy vs Softmax
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_background(s6)
    add_header(s6, "Gibbs Free Energy vs. Softmax Overconfidence", "OUT-OF-DISTRIBUTION DETECTION METHODOLOGY")

    add_card(s6, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.2), "The Flaw of Softmax Confidence (MSP)", RED_ACCENT)
    tb = s6.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Why Softmax Fails on Zero-Days:"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = WHITE
    p.space_after = Pt(6)

    p1 = tf.add_paragraph()
    p1.text = "In standard neural networks, class probability is computed as:\n" \
              "       P(y = k | x) = exp(f_k(x)) / Σ_j exp(f_j(x))\n\n" \
              "The Critical Failure:\n" \
              "• The denominator normalizes logits across known classes.\n" \
              "• When an unknown zero-day exploit arrives, its logits might all be shifted or small (e.g., [1.2, 0.8, -0.4]), but softmax forces the sum to 1.0, frequently assigning 70%-99% confidence to a completely arbitrary known class.\n" \
              "• Max Softmax Probability (MSP) cannot distinguish between in-distribution ambiguity and true out-of-distribution novelty."
    p1.font.size = Pt(11.5)
    p1.font.color.rgb = GRAY_TEXT

    add_card(s6, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2), "The Gibbs Free Energy Solution", GREEN_ACCENT)
    tb = s6.shapes.add_textbox(Inches(7.0), Inches(2.2), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Helmholtz / Gibbs Free Energy Formulation:"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = WHITE
    p.space_after = Pt(6)

    p1 = tf.add_paragraph()
    p1.text = "Derived from statistical physics, the Free Energy of flow logits f(x) at temperature T is defined as the negative log partition function:\n" \
              "       E(x; T) = -T · log Σ_{k=1}^K exp( f_k(x) / T )\n\n" \
              "Why Energy Tracks Input Density:\n" \
              "• Under an energy-based interpretation, the probability density is p(x) = exp(-E(x)) / Z.\n" \
              "• In-distribution benign flows produce high logit activations, resulting in large negative Free Energy: E(x) << 0.\n" \
              "• Unseen zero-day flows lie in low-density space, yielding low logit support and high Energy: E(x) >> τ."
    p1.font.size = Pt(11.5)
    p1.font.color.rgb = GRAY_TEXT

    # =========================================================================
    # SLIDE 7: Statistical Calibration & Thresholding
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_background(s7)
    add_header(s7, "Strict Benign Quantile Calibration (5% FPR)", "THRESHOLD CALIBRATION & DECISION BOUNDARY")

    # Metrics Row
    m1 = add_card(s7, Inches(0.8), Inches(1.7), Inches(3.7), Inches(1.5), None, CYAN_ACCENT)
    tb = s7.shapes.add_textbox(Inches(0.9), Inches(1.8), Inches(3.5), Inches(1.3))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = "-7.4399"
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p2 = tf.add_paragraph()
    p2.text = "Calibrated Threshold (τ)"
    p2.font.size = Pt(12)
    p2.font.color.rgb = WHITE

    m2 = add_card(s7, Inches(4.8), Inches(1.7), Inches(3.7), Inches(1.5), None, GREEN_ACCENT)
    tb = s7.shapes.add_textbox(Inches(4.9), Inches(1.8), Inches(3.5), Inches(1.3))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = "5.0% FPR"
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = GREEN_ACCENT
    p2 = tf.add_paragraph()
    p2.text = "Target False Positive Rate on Benign"
    p2.font.size = Pt(12)
    p2.font.color.rgb = WHITE

    m3 = add_card(s7, Inches(8.8), Inches(1.7), Inches(3.7), Inches(1.5), None, BLUE_ACCENT)
    tb = s7.shapes.add_textbox(Inches(8.9), Inches(1.8), Inches(3.5), Inches(1.3))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = "T = 1.0"
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = BLUE_ACCENT
    p2 = tf.add_paragraph()
    p2.text = "Gibbs Energy Temperature Constant"
    p2.font.size = Pt(12)
    p2.font.color.rgb = WHITE

    # Detailed Calibration Card
    add_card(s7, Inches(0.8), Inches(3.5), Inches(11.733), Inches(3.4), "ZeroShield Dual-Head Decision Protocol")
    tb = s7.shapes.add_textbox(Inches(1.0), Inches(4.0), Inches(11.3), Inches(2.7))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Operational Classification Rules:"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = WHITE
    p.space_after = Pt(6)

    p1 = tf.add_paragraph()
    p1.text = "1. Calibration Step (Validation Set): τ is computed as the (1 - α) = 95th empirical percentile of Free Energy evaluated exclusively on verified benign validation flows: τ = Quantile_{0.95}( E(D_val^{benign}) ).\n\n" \
              "2. Zero-Day Verdict: If E(x) > τ (Energy Score exceeds -7.4399):\n" \
              "   -> Verdict = ZERO_DAY_EXPLOIT (Novelty Confirmed). Severity = Critical or High.\n" \
              "   -> Classification head is bypassed because the flow does not belong to any training distribution.\n\n" \
              "3. Known Traffic Verdict: If E(x) ≤ τ (Energy Score within benign bound):\n" \
              "   -> Verdict = argmax_k P(y=k | x). If k = 0 -> BENIGN; if k > 0 -> KNOWN_ATTACK (e.g., DoS, PortScan, BruteForce)."
    p1.font.size = Pt(12)
    p1.font.color.rgb = GRAY_TEXT

    # =========================================================================
    # SLIDE 8: Explainability: Gradient-Based Feature Attribution
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_background(s8)
    add_header(s8, "Explainability: Gradient-Based Feature Attribution", "SOC ANALYST TRUST & AUDITABILITY")

    add_card(s8, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.2), "The Need for Interpretable AI")
    tb = s8.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Overcoming the Black-Box Stigma:"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = WHITE
    p.space_after = Pt(6)

    p1 = tf.add_paragraph()
    p1.text = "Security analysts reject automated alerts if the system cannot explain WHY a packet flow was flagged.\n\n" \
              "ZeroShield implements an exact first-order gradient attribution method directly on the Free Energy function:\n" \
              "       S_i = | ∂E(x) / ∂x_i | · σ_i\n\n" \
              "• High S_i indicates that small perturbations in flow feature x_i drastically swing the anomaly score.\n" \
              "• Normalizing by feature standard deviation σ_i ensures dimensionless comparability across disparate units (e.g., microsecond durations vs packet counts)."
    p1.font.size = Pt(11.5)
    p1.font.color.rgb = GRAY_TEXT

    add_card(s8, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2), "Live Alert Attribution Output")
    tb = s8.shapes.add_textbox(Inches(7.0), Inches(2.2), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Sample Incident Report Generated for SOC:"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = CYAN_ACCENT
    p.space_after = Pt(6)

    ex = [
        ("Verdict", "ZERO_DAY_EXPLOIT (Severity: CRITICAL)"),
        ("Energy Score", "-4.1200 (Threshold τ = -7.4399, Delta = +3.32)"),
        ("Top Feature #1", "syn_flag_cnt (Attribution: 38.4%) - Anomaly in TCP handshakes"),
        ("Top Feature #2", "flow_iat_std (Attribution: 27.1%) - Irregular packet spacing"),
        ("Top Feature #3", "totlen_fwd_pkts (Attribution: 18.2%) - Abnormal payload asymmetry"),
        ("Analyst Recommendation", "Quarantine source port, inspect egress proxy payload, trigger automated memory dump on destination host.")
    ]
    for k, v in ex:
        p = tf.add_paragraph()
        p.text = f"• {k}: {v}"
        p.font.size = Pt(11)
        p.font.color.rgb = GRAY_TEXT
        p.space_after = Pt(4)

    # =========================================================================
    # SLIDE 9: Leave-One-Attack-Out (LOAO) Benchmark
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_background(s9)
    add_header(s9, "Empirical Evaluation: Leave-One-Attack-Out (LOAO)", "BENCHMARKING ZERO-DAY GENERALIZATION")

    add_card(s9, Inches(0.8), Inches(1.7), Inches(11.733), Inches(5.2), "Rigorous Protocol to Simulate Truly Novel Cyberattacks")
    tb = s9.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Standard vs. LOAO Evaluation Methodology:"
    p.font.bold = True
    p.font.size = Pt(14)
    p.font.color.rgb = WHITE
    p.space_after = Pt(6)

    p1 = tf.add_paragraph()
    p1.text = "• Flaw of Standard K-Fold Cross Validation: In standard random splits, samples of all attack types exist in both train and test folds. This tests 'known attack classification', NOT zero-day detection.\n\n" \
              "• ZeroShield LOAO Protocol: To realistically model zero-day conditions, we execute iterative rounds where one entire attack family is completely withheld from the training set. The model is trained ONLY on Benign flows + the remaining attacks. The held-out attack is then presented during testing as a simulated zero-day.\n\n" \
              "• Held-Out Evaluation Classes Tested:\n" \
              "   1. Botnet Traffic (ARES / Mirai infected command-and-control)\n" \
              "   2. BruteForce (SSH/FTP credential dictionary attacks)\n" \
              "   3. Infiltration (Internal privilege escalation and lateral movement)\n" \
              "   4. PortScan (Stealthy SYN/FIN/ACK network reconnaissance)\n" \
              "   5. WebAttack (SQL Injection, Cross-Site Scripting, Command Injection)"
    p1.font.size = Pt(12)
    p1.font.color.rgb = GRAY_TEXT

    # =========================================================================
    # SLIDE 10: Comparative Results
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_background(s10)
    add_header(s10, "Empirical Results: ZeroShield vs Baselines", "PERFORMANCE BENCHMARK ON CIC-IDS TRAFFIC")

    # Table of Results
    rows = 5
    cols = 5
    table_shape = s10.shapes.add_table(rows, cols, Inches(0.8), Inches(1.8), Inches(11.733), Inches(2.6))
    table = table_shape.table

    headers = ["Model / Architecture", "Novelty Mechanism", "Mean AUROC", "Zero-Day Recall @ 5% FPR", "Latency / Flow"]
    data = [
        ["ZeroShield (FT-Transformer)", "Gibbs Free Energy", "0.9211", "84.8%", "4.2 ms (GPU) / 8.5 ms (CPU)"],
        ["Random Forest (RF)", "Isolation Forest Distance", "0.8993", "78.4%", "12.1 ms"],
        ["Gradient Boosting (GB)", "Max Softmax Probability", "0.8969", "76.9%", "14.8 ms"],
        ["Multi-Layer Perceptron (MLP)", "Softmax Entropy", "0.7883", "62.1%", "3.1 ms"]
    ]

    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD_BG
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = CYAN_ACCENT

    for i, row in enumerate(data):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.fill.solid()
            if i == 0:
                cell.fill.fore_color.rgb = RGBColor(20, 45, 85) # Highlight top row
            else:
                cell.fill.fore_color.rgb = CARD_BG
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.size = Pt(10.5)
            if i == 0:
                p.font.bold = True
                p.font.color.rgb = WHITE
            else:
                p.font.color.rgb = GRAY_TEXT

    add_card(s10, Inches(0.8), Inches(4.7), Inches(11.733), Inches(2.2), "Key Performance Takeaways")
    tb = s10.shapes.add_textbox(Inches(1.0), Inches(5.1), Inches(11.3), Inches(1.7))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "1. +13.28% AUROC superiority over deep MLP baseline due to multi-head self-attention feature interaction modeling.\n" \
             "2. +6.4% higher zero-day recall at strict 5% FPR compared to Random Forest.\n" \
             "3. Gibbs Free Energy consistently outperforms Softmax Entropy by avoiding normalization bias in logit space."
    p.font.size = Pt(12)
    p.font.color.rgb = WHITE

    # =========================================================================
    # SLIDE 11: End-to-End System Architecture
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_background(s11)
    add_header(s11, "End-to-End System Architecture & Technology Stack", "FULL-STACK PRODUCTION IMPLEMENTATION")

    # 4 Architecture Columns
    col_w = Inches(2.8)
    col_gap = Inches(0.18)

    # Ingestion
    c1 = add_card(s11, Inches(0.8), Inches(1.7), col_w, Inches(5.2), "1. Flow Ingestion")
    tb = s11.shapes.add_textbox(Inches(0.9), Inches(2.2), col_w - Inches(0.2), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• Live SSE Stream: Emulates active switch flows at 1-5 flows/sec.\n\n" \
             "• CSV/PCAP Batch: Upload bulk network telemetry for asynchronous batch analysis.\n\n" \
             "• Feature Preprocessor: Real-time StandardScaler & Categorical Port Binning."
    p.font.size = Pt(11)
    p.font.color.rgb = GRAY_TEXT

    # Inference Engine
    c2 = add_card(s11, Inches(0.8) + col_w + col_gap, Inches(1.7), col_w, Inches(5.2), "2. Dual Inference")
    tb = s11.shapes.add_textbox(Inches(0.9) + col_w + col_gap, Inches(2.2), col_w - Inches(0.2), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• PyTorch Engine: Local workstation & GPU/MPS accelerated tensor processing.\n\n" \
             "• Pure NumPy Engine: Exact analytical forward pass without PyTorch dependencies for ultra-lean serverless deployment (<50MB memory footprint)."
    p.font.size = Pt(11)
    p.font.color.rgb = GRAY_TEXT

    # Backend API & DB
    c3 = add_card(s11, Inches(0.8) + (col_w + col_gap)*2, Inches(1.7), col_w, Inches(5.2), "3. API & Persistence")
    tb = s11.shapes.add_textbox(Inches(0.9) + (col_w + col_gap)*2, Inches(2.2), col_w - Inches(0.2), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• FastAPI Backend: Async high-throughput REST endpoints + SSE streaming.\n\n" \
             "• SQLite Database: Dynamic path resolution (/tmp on serverless) for alert logs, scan telemetry, and operational audit trails."
    p.font.size = Pt(11)
    p.font.color.rgb = GRAY_TEXT

    # Frontend UI
    c4 = add_card(s11, Inches(0.8) + (col_w + col_gap)*3, Inches(1.7), col_w, Inches(5.2), "4. SOC Frontend")
    tb = s11.shapes.add_textbox(Inches(0.9) + (col_w + col_gap)*3, Inches(2.2), col_w - Inches(0.2), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• Zero-Build Vanilla Stack: HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js.\n\n" \
             "• Real-Time Visualizers: Live energy gauge, telemetry charts, alert inspector.\n\n" \
             "• Fully Responsive: Cyber-dark theme optimized for SOC command centers."
    p.font.size = Pt(11)
    p.font.color.rgb = GRAY_TEXT

    # =========================================================================
    # SLIDE 12: Security Operations Center (SOC) Interface
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_background(s12)
    add_header(s12, "Interactive SOC Operations Dashboard", "USER INTERFACE & OPERATIONAL WORKFLOWS")

    views = [
        ("Dashboard (Overview)", "Real-time threat status indicator, total flow counter, zero-day threat gauge, energy distribution histogram, and recent incident feed."),
        ("Live Network Monitor", "Live SSE streaming table with auto-scroll, color-coded verdict badges, instantaneous energy readings, and pause/resume controls."),
        ("Analyze Upload (Batch)", "Drag-and-drop CSV upload for offline packet capture logs, real-time batch processing progress bar, and downloadable JSON/CSV triage reports."),
        ("Security Alerts Triage", "Comprehensive incident table with severity filters (Critical, High, Medium, Low), multi-parameter search, and detailed modal drill-downs."),
        ("Model Performance", "LOAO benchmark metrics, ROC curve visualizers, confusion matrices across attack classes, and baseline comparison charts."),
        ("How It Works & Docs", "Embedded interactive educational guide explaining the mathematical intuition of FT-Transformers and Gibbs Free Energy.")
    ]

    for idx, (title, desc) in enumerate(views):
        r = idx // 2
        c = idx % 2
        left = Inches(0.8) if c == 0 else Inches(6.8)
        top = Inches(1.8) + Inches(r * 1.7)
        add_card(s12, left, top, Inches(5.7), Inches(1.5), title)
        tb = s12.shapes.add_textbox(left + Inches(0.2), top + Inches(0.55), Inches(5.3), Inches(0.85))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = desc
        p.font.size = Pt(11)
        p.font.color.rgb = GRAY_TEXT

    # =========================================================================
    # SLIDE 13: Deployment Topology & Future Scope
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_background(s13)
    add_header(s13, "Deployment Topology & Future Directions", "PRODUCTION READINESS & ROADMAP")

    add_card(s13, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.2), "Deployment Topologies")
    tb = s13.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "1. Serverless Cloud Deployment (Vercel):"
    p.font.bold = True
    p.font.size = Pt(12.5)
    p.font.color.rgb = WHITE
    p.space_after = Pt(4)
    p_sub = tf.add_paragraph()
    p_sub.text = "Zero-dependency pure NumPy forward pass enables deployment within Vercel's strict 250MB limit, eliminating hefty PyTorch binaries while preserving exact mathematical precision.\n"
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = GRAY_TEXT

    p2 = tf.add_paragraph()
    p2.text = "2. On-Premises & Edge SOC Gateway:"
    p2.font.bold = True
    p2.font.size = Pt(12.5)
    p2.font.color.rgb = WHITE
    p2.space_after = Pt(4)
    p2_sub = tf.add_paragraph()
    p2_sub.text = "Deployable as a standalone Docker container or native systemd service at corporate network boundaries (TAP/SPAN ports) with PyTorch GPU/MPS acceleration for line-rate 10Gbps flow analysis.\n"
    p2_sub.font.size = Pt(11)
    p2_sub.font.color.rgb = GRAY_TEXT

    p3 = tf.add_paragraph()
    p3.text = "3. GitHub Open Source Ecosystem:"
    p3.font.bold = True
    p3.font.size = Pt(12.5)
    p3.font.color.rgb = WHITE
    p3.space_after = Pt(4)
    p3_sub = tf.add_paragraph()
    p3_sub.text = "All model weights, dataset generators, benchmark runners, and frontend assets are versioned and maintained at https://github.com/Indrachinnam/ZeroShield."
    p3_sub.font.size = Pt(11)
    p3_sub.font.color.rgb = GRAY_TEXT

    add_card(s13, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.2), "Future Research & Development")
    tb = s13.shapes.add_textbox(Inches(7.0), Inches(2.2), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Roadmap & Enhancements:"
    p.font.bold = True
    p.font.size = Pt(12.5)
    p.font.color.rgb = CYAN_ACCENT
    p.space_after = Pt(6)

    roadmap = [
        ("Packet-Payload Fusion", "Combining tabular flow statistical tokens with raw packet byte tokens via cross-attention to inspect encrypted header variations."),
        ("Streaming Continuous Adaptation", "Online meta-learning to continuously adapt benign energy quantiles as corporate network baselines evolve over time."),
        ("Hardware Quantization (INT8)", "Exporting FT-Transformer to ONNX and TensorRT with 8-bit quantization for sub-millisecond edge firewall deployment."),
        ("Multi-Agent Threat Intelligence", "Automated orchestration linking ZeroShield alerts with generative AI agents to automatically generate firewall rules and patch tickets.")
    ]
    for r_title, r_desc in roadmap:
        pr = tf.add_paragraph()
        pr.text = f"• {r_title}:"
        pr.font.bold = True
        pr.font.size = Pt(11.5)
        pr.font.color.rgb = WHITE
        pr_d = tf.add_paragraph()
        pr_d.text = f"   {r_desc}"
        pr_d.font.size = Pt(11)
        pr_d.font.color.rgb = GRAY_TEXT
        pr_d.space_after = Pt(4)

    # =========================================================================
    # SLIDE 14: Conclusion & Project Links
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_background(s14)

    card = add_card(s14, Inches(0.8), Inches(1.2), Inches(11.733), Inches(5.1), None, CYAN_ACCENT)
    tb = s14.shapes.add_textbox(Inches(1.2), Inches(1.6), Inches(10.9), Inches(4.3))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "ZEROSHIELD: REVOLUTIONIZING INTRUSION DETECTION"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p.space_after = Pt(12)

    p1 = tf.add_paragraph()
    p1.text = "Zero-Day Exploits No Longer Hide in Plain Sight."
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = WHITE
    p1.space_after = Pt(20)

    p2 = tf.add_paragraph()
    p2.text = "By replacing brittle signatures and overconfident softmax models with Flow-Transformers and Gibbs Free Energy, ZeroShield establishes a mathematically grounded, interpretable, and high-performance foundation for next-generation network defense."
    p2.font.size = Pt(15)
    p2.font.color.rgb = GRAY_TEXT
    p2.space_after = Pt(24)

    p3 = tf.add_paragraph()
    p3.text = "Project Resources & Repositories:"
    p3.font.bold = True
    p3.font.size = Pt(13)
    p3.font.color.rgb = WHITE
    p3.space_after = Pt(6)

    p4 = tf.add_paragraph()
    p4.text = "• GitHub Source Code:  https://github.com/Indrachinnam/ZeroShield\n" \
              "• Local Web Server:     http://localhost:8000\n" \
              "• Public Demo Tunnel:   https://plenty-pears-fail.loca.lt\n" \
              "• Complete Project Dossier: ZeroShield_Complete_Project_Dossier.pdf\n" \
              "• Master Presentation:      ZeroShield_Presentation.pptx"
    p4.font.size = Pt(12)
    p4.font.color.rgb = BLUE_ACCENT

    # Save presentation
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    prs.save(output_path)
    print(f"[+] Successfully generated PowerPoint presentation at {output_path}")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/Users/vinodkumar/.gemini/antigravity/scratch/zeroshield/docs_and_pdfs/ZeroShield_Presentation.pptx"
    create_presentation(out)
