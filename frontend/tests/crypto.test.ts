import { beforeAll, describe, expect, it } from "vitest";
import {
  PBKDF2_ITERATIONS,
  encryptBytes,
} from "../../scripts/stasis-envelope.mjs";
import { decryptEnvelope } from "../src/downloads/crypto";

const passphrase = "violet museum harbor transit copper lantern";
const plaintext = new TextEncoder().encode("generated browser crypto fixture");
let envelope: Awaited<ReturnType<typeof encryptBytes>>;

beforeAll(async () => {
  envelope = await encryptBytes(plaintext, passphrase);
});

describe("browser-compatible encryption", () => {
  it("uses the documented high production PBKDF2 work factor", () => {
    expect(PBKDF2_ITERATIONS).toBe(600_000);
  });

  it("round-trips an encrypted payload", async () => {
    const decrypted = await decryptEnvelope(envelope, passphrase);
    expect(new TextDecoder().decode(decrypted)).toBe("generated browser crypto fixture");
  });

  it("fails authenticated decryption with an incorrect passphrase", async () => {
    await expect(
      decryptEnvelope(envelope, "wrong museum harbor transit copper lantern"),
    ).rejects.toThrow();
  });

  it("fails authenticated decryption after ciphertext tampering", async () => {
    const tampered = structuredClone(envelope);
    const ciphertext = Buffer.from(tampered.ciphertext, "base64");
    ciphertext[0] ^= 1;
    tampered.ciphertext = ciphertext.toString("base64");
    await expect(decryptEnvelope(tampered, passphrase)).rejects.toThrow();
  });

  it("uses fresh salts and IVs on every encryption", async () => {
    const next = await encryptBytes(plaintext, passphrase, { iterations: 100_000 });
    expect(next.kdf.salt).not.toBe(envelope.kdf.salt);
    expect(next.cipher.iv).not.toBe(envelope.cipher.iv);
  });
});
