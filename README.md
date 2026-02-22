# 🃏 7K Rebirth Card Match Helper

<img width="568" height="363" alt="Screenshot 2026-02-21 220810" src="https://github.com/user-attachments/assets/4777d861-0775-405e-9530-cda865a1388c" />


A sleek, AI-powered computer vision utility designed to effortlessly solve the 24-card (3x8) matching mini-game in 7K Rebirth. Built entirely in Python, this tool acts as a highly intelligent screen-reader that mathematically reconstructs the game grid and perfectly captures the face-up state of every card.

## ✨ Core Features
* **Intelligent Auto-Capture:** Uses OpenCV to buffer game frames, analyzing edge geometry and HSV brightness to flawlessly extract the face-up artwork of all 24 cards.
* **Mathematical Grid Reconstruction:** Bypasses in-game lighting and visual effects by dynamically calculating median gaps to hallucinate and reconstruct missing card bounds perfectly.
* **Premium Glassmorphism UI:** Features a luxurious, Apple-inspired translucent dark mode interface built with PyQt6.
* **F2 Global Hotkey:** Control the buffer instantly without tabbing out of the game.
* **Auto-UAC Elevation:** Automatically requests Windows Administrator privileges to ensure keyboard hooks bypass strict game anti-cheat and DirectInput blockers.
* **Visual Debugging:** Automatically saves timestamped visual proofs to a local `debug_logs` folder to easily tune aspect ratios and bounding boxes.

---

## 🎮 How to Use (For Regular Users)
You **do not** need to install Python or know how to code to use this helper! 

1. Go to the [Releases](../../releases) tab on the right side of this GitHub page.
2. Download the latest `7K_Card_AI_Tracker.exe` file.
3. Run the `.exe`. *(Note: Windows will ask for Administrator permissions. This is required so the tool can hear your F2 hotkey while the game is focused).*
4. Once the sleek UI appears, open your game and start the card matching mini-game.
5. As soon as the cards start flipping face-up, press **`F2`** to start recording. 
6. Wait for all 24 cards to fully reveal themselves, then press **`F2`** again to stop.
7. The AI will instantly calculate the grid and pop up a translucent solution cheat sheet right on your screen!

---

## 💻 How to Run from Source (For Developers)

If you want to read the OpenCV logic, tweak the Laplacian variances, or compile the tool yourself, follow these steps:

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Setup the Environment
Clone the repository and set up a virtual environment:
```bash
git clone [https://github.com/xxdadixx/7K_CardGame_Helper.git](https://github.com/xxdadixx/7K_CardGame_Helper.git)
cd 7K-Card-Helper
python -m venv venv
