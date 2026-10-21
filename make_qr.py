import qrcode

website = "https://bpseduvision.streamlit.app/"

qr = qrcode.QRCode(
    version=None,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=15,
    border=4
)

qr.add_data(website)
qr.make(fit=True)

image = qr.make_image(
    fill_color="black",
    back_color="white"
)

image.save("EduVision_QR.png")


import qrcode

website = "https://bpseduvision.streamlit.app/"

qr = qrcode.QRCode(
    version=None,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=15,
    border=4
)

qr.add_data(website)
qr.make(fit=True)

image = qr.make_image(
    fill_color="black",
    back_color="white"
)

image.save("EduVision_QR.png")

print("EduVision QR code created!")