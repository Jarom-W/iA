import { webcrypto } from "node:crypto";

export const ENVELOPE_FORMAT = "stasis-encrypted-download";
export const ENVELOPE_VERSION = 1;
export const PBKDF2_ITERATIONS = 600_000;
export const SALT_BYTES = 16;
export const IV_BYTES = 12;
export const TAG_LENGTH = 128;
export const ENVELOPE_AAD = new TextEncoder().encode(
  `${ENVELOPE_FORMAT}:v${ENVELOPE_VERSION}`,
);

function toBase64(bytes) {
  return Buffer.from(bytes).toString("base64");
}

export async function encryptBytes(
  plaintext,
  passphrase,
  { iterations = PBKDF2_ITERATIONS, crypto = webcrypto } = {},
) {
  if (!ArrayBuffer.isView(plaintext) || plaintext.BYTES_PER_ELEMENT !== 1) {
    throw new TypeError("Plaintext must be a Uint8Array.");
  }
  if (typeof passphrase !== "string" || passphrase.length === 0) {
    throw new TypeError("A passphrase is required.");
  }

  const salt = crypto.getRandomValues(new Uint8Array(SALT_BYTES));
  const iv = crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const passphraseBytes = new TextEncoder().encode(passphrase);
  let keyMaterial;
  try {
    keyMaterial = await crypto.subtle.importKey(
      "raw",
      passphraseBytes,
      "PBKDF2",
      false,
      ["deriveKey"],
    );
  } finally {
    passphraseBytes.fill(0);
  }
  const key = await crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      hash: "SHA-256",
      salt,
      iterations,
    },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt"],
  );
  const ciphertext = await crypto.subtle.encrypt(
    {
      name: "AES-GCM",
      iv,
      additionalData: ENVELOPE_AAD,
      tagLength: TAG_LENGTH,
    },
    key,
    plaintext,
  );

  return {
    format: ENVELOPE_FORMAT,
    version: ENVELOPE_VERSION,
    kdf: {
      name: "PBKDF2",
      hash: "SHA-256",
      iterations,
      salt: toBase64(salt),
    },
    cipher: {
      name: "AES-GCM",
      iv: toBase64(iv),
      tagLength: TAG_LENGTH,
    },
    ciphertext: toBase64(new Uint8Array(ciphertext)),
  };
}

export async function encryptJson(value, passphrase, options) {
  const plaintext = new TextEncoder().encode(JSON.stringify(value));
  try {
    return await encryptBytes(plaintext, passphrase, options);
  } finally {
    plaintext.fill(0);
  }
}
