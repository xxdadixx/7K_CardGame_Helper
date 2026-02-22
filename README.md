# 🃏 7K Rebirth Card Match Helper

<img width="568" height="363" alt="Screenshot 2026-02-21 220810" src="https://github.com/user-attachments/assets/4777d861-0775-405e-9530-cda865a1388c" />

A sleek, AI-powered computer vision utility designed to effortlessly solve the 24-card (3x8) matching mini-game in 7K Rebirth. Built entirely in Python, this tool acts as a highly intelligent screen-reader that mathematically reconstructs the game grid and perfectly captures the face-up state of every card.

โปรแกรมช่วยเล่นมินิเกมจับคู่ไพ่ 24 ใบ (3x8) ในเกม 7K Rebirth ที่ขับเคลื่อนด้วยระบบ AI (Computer Vision) เขียนด้วย Python ทั้งหมด โปรแกรมนี้ทำงานเสมือนตาที่คอยอ่านหน้าจอ โดยใช้หลักการทางคณิตศาสตร์จำลองกรอบของไพ่และจับภาพไพ่ตอนหงายหน้าได้อย่างสมบูรณ์แบบ

---

## ✨ Core Features | ฟีเจอร์หลัก

* **Intelligent Auto-Capture:** Uses OpenCV to buffer game frames, analyzing edge geometry and HSV brightness to flawlessly extract the face-up artwork of all 24 cards.
* **Mathematical Grid Reconstruction:** Bypasses in-game lighting and visual effects by dynamically calculating median gaps to hallucinate and reconstruct missing card bounds perfectly.
* **Premium Glassmorphism UI:** Features a luxurious, Apple-inspired translucent dark mode interface built with PyQt6.
* **F2 Global Hotkey:** Control the buffer instantly without tabbing out of the game.
* **Auto-UAC Elevation:** Automatically requests Windows Administrator privileges to ensure keyboard hooks bypass strict game anti-cheat and DirectInput blockers.
* **Visual Debugging:** Automatically saves timestamped visual proofs to a local `debug_logs` folder to easily tune aspect ratios and bounding boxes.

* **จับภาพอัจฉริยะ (Intelligent Auto-Capture):** ใช้ OpenCV บันทึกเฟรมภาพในเกม วิเคราะห์ขอบเขตและความสว่าง (HSV) เพื่อดึงภาพหน้าไพ่ทั้ง 24 ใบออกมาได้อย่างไร้ที่ติ
* **จำลองกริดด้วยคณิตศาสตร์ (Grid Reconstruction):** ข้ามขีดจำกัดเรื่องแสงเงาและเอฟเฟกต์ในเกม โดยการคำนวณระยะห่างเพื่อเติมเต็มตำแหน่งไพ่ที่ระบบมองไม่ชัดให้ครบถ้วน
* **ดีไซน์พรีเมียม (Glassmorphism UI):** หน้าต่างโปรแกรมสวยหรูแบบโปร่งแสง (Dark Mode) สไตล์ Apple พัฒนาด้วย PyQt6
* **ปุ่มลัดระดับโกลบอล (F2 Hotkey):** ควบคุมการทำงานได้ทันทีโดยไม่ต้องสลับหน้าจอ (Alt+Tab) ออกจากเกม
* **ขอสิทธิ์ Admin อัตโนมัติ (Auto-UAC):** ระบบจะขอสิทธิ์ Administrator ใน Windows อัตโนมัติ เพื่อให้ดักจับปุ่มกดทะลุระบบป้องกันของเกม (DirectInput) ได้
* **ระบบตรวจสอบภาพ (Visual Debugging):** บันทึกภาพพร้อมระบุเวลาลงโฟลเดอร์ `debug_logs` อัตโนมัติ เพื่อให้ง่ายต่อการปรับตั้งค่าและตรวจสอบความแม่นยำ

---

## 🎮 How to Use (For Regular Users) | วิธีใช้งาน (สำหรับผู้ใช้ทั่วไป)

You **do not** need to install Python or know how to code to use this helper! 
คุณ **ไม่จำเป็น** ต้องติดตั้ง Python หรือเขียนโค้ดเป็นก็สามารถใช้งานได้!

1. Go to the [Releases](../../releases) tab on the right side of this GitHub page.
   *(ไปที่แท็บ Releases ทางด้านขวาของหน้า GitHub นี้)*
2. Download the latest `7K_Card_AI_Tracker.exe` file.
   *(ดาวน์โหลดไฟล์ .exe เวอร์ชันล่าสุด)*
3. Run the `.exe`. (Note: Windows will ask for Administrator permissions. This is required so the tool can hear your F2 hotkey while the game is focused).
   *(เปิดโปรแกรมใช้งานได้เลย Windows จะเด้งถามสิทธิ์ Administrator ให้กดยอมรับ เพื่อให้โปรแกรมสามารถรับคำสั่งปุ่ม F2 ขณะเล่นเกมได้)*
4. Once the sleek UI appears, open your game and start the card matching mini-game.
   *(เมื่อหน้าต่างโปรแกรมเปิดขึ้นมา ให้เข้าเกมและเริ่มมินิเกมจับคู่ไพ่)*
5. As soon as the cards start flipping face-up, press **`F2`** to start recording. 
   *(ทันทีที่ไพ่เริ่มหงายหน้าขึ้น ให้กดปุ่ม **`F2`** เพื่อเริ่มบันทึกภาพ)*
6. Wait for all 24 cards to fully reveal themselves, then press **`F2`** again to stop.
   *(รอจนไพ่ทั้ง 24 ใบหงายหน้าครบทั้งหมด แล้วกดปุ่ม **`F2`** อีกครั้งเพื่อหยุด)*
7. The AI will instantly calculate the grid and pop up a translucent solution cheat sheet right on your screen!
   *(AI จะคำนวณตำแหน่งและแสดงหน้าต่างเฉลยแบบโปร่งแสงขึ้นมาบนหน้าจอคุณทันที!)*

---

## 💻 How to Run from Source (For Developers) | วิธีรันโค้ดด้วยตัวเอง

If you want to read the OpenCV logic, tweak the Laplacian variances, or compile the tool yourself, follow these steps:
*(หากคุณต้องการปรับแต่งระบบ OpenCV, แก้ไขค่าความคลาดเคลื่อน หรือคอมไพล์โปรแกรมด้วยตัวเอง ทำตามขั้นตอนดังนี้:)*

### 1. Prerequisites | สิ่งที่ต้องเตรียม
Ensure you have Python 3.10+ installed.
*(โปรดแน่ใจว่าติดตั้ง Python 3.10 ขึ้นไปไว้ในเครื่องแล้ว)*

### 2. Setup the Environment | การตั้งค่า Environment
Clone the repository and set up a virtual environment:
*(โคลน Repository และสร้าง Virtual Environment:)*

```bash
git clone [https://github.com/xxdadixx/7K_CardGame_Helper.git](https://github.com/xxdadixx/7K_CardGame_Helper.git)
cd 7K_CardGame_Helper
python -m venv venv
