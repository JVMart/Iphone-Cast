# Privacy Policy — Iphone-Cast

**Effective date:** 2026-05-25
**Publisher:** JVMart
**Contact:** josevictormadrid90@gmail.com
**Project repository:** https://github.com/JVMart/Iphone-Cast

## 1. Summary

Iphone-Cast is a Windows desktop application that lets your iPhone mirror its
screen to your PC over a local Wi-Fi network (AirPlay 2 protocol). The
application runs entirely on your local PC. It does not collect, store, or
transmit personal information to the publisher or to any remote service.

## 2. Data we collect

We do not collect any personal information. The application does not require an
account, does not communicate with publisher-operated servers (we operate none),
and does not contain advertising, analytics, or telemetry SDKs.

The application performs the following strictly local activities that may
involve information about your device or network session:

- **mDNS / Bonjour service advertisement.** When you start the receiver, the
  application announces a service (default name "PC-Cast") on your local
  network so your iPhone can discover the PC. This advertisement is visible
  only to devices on the same local network and is required for the feature
  to work. You can change or hide this name in `config.py`.
- **Receiving the mirror stream.** Video and audio frames from your iPhone are
  received over your local network and decoded for on-screen display. The
  stream is not recorded, persisted, or transmitted elsewhere.
- **In-memory diagnostic log.** The underlying receiver (UxPlay) prints
  diagnostic lines that the application displays in its log window. This log
  exists only in the running process; it is not written to disk by
  Iphone-Cast and is discarded when you close the application.

## 3. Data we share

None. We do not share data with third parties because we do not collect any.

## 4. Third-party components

Iphone-Cast bundles or depends on open-source components, each governed by its
own license. None of these components, in the configuration shipped with
Iphone-Cast, contact publisher-operated servers:

- **UxPlay** — open-source AirPlay 2 receiver (GPL v3).
  https://github.com/FDH2/UxPlay
- **GStreamer** — multimedia framework (LGPL v2.1).
  https://gstreamer.freedesktop.org/
- **Apple Bonjour** — required runtime for mDNS service discovery. Apple's
  privacy policy applies to the Bonjour service:
  https://www.apple.com/legal/privacy/

## 5. Cookies, trackers, advertising

The application does not use cookies, web trackers, or advertising SDKs.

## 6. Children's privacy

The application does not knowingly collect any information from anyone,
including children under 13. The Children's Online Privacy Protection Act
(COPPA) does not apply because no data is collected.

## 7. Security

Because no personal data is collected or transmitted, Iphone-Cast does not
introduce data-security risk. The AirPlay 2 handshake between your iPhone and
the PC uses the cryptographic authentication implemented by UxPlay. Refer to
UxPlay's documentation for technical details.

## 8. Your rights (GDPR / CCPA / UK GDPR)

Since the application does not collect personal data, there is no personal
data for the publisher to provide, rectify, port, or erase. If you believe you
have a privacy concern related to this application, contact us at the address
above and we will respond within a reasonable time.

## 9. Changes to this policy

We may update this policy if the application's behavior changes in a way that
affects privacy (for example, if a future version adds an optional remote
feature). Updates will be published at the same URL where you found this
policy, with a new effective date. Substantive changes will be summarized in
the project's GitHub release notes.

## 10. Contact

Questions about this policy: open an issue at
https://github.com/JVMart/Iphone-Cast/issues or email
josevictormadrid90@gmail.com.
