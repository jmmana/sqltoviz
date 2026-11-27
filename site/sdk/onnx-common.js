const SCHEMA = { chart: { input: "table_features", output: "chart_scores", inWidth: 32, outWidth: 10 }, role: { input: "column_features", output: "role_scores", inWidth: 28, outWidth: 5 } };
export class ModelError extends Error {
    constructor(m) { super(m); this.name = "ModelError"; }
}
export async function sha256Hex(bytes) {
    const subtle = globalThis.crypto?.subtle;
    if (subtle) {
        const d = new Uint8Array(await subtle.digest("SHA-256", bytes));
        return Array.from(d, (b) => b.toString(16).padStart(2, "0")).join("");
    }
    const name = "node:crypto";
    const { createHash } = (await import(name));
    return createHash("sha256").update(bytes).digest("hex");
}
export async function verifiedSession(ort, bytes, expectedSha256, kind, options) {
    if (!expectedSha256 || (await sha256Hex(bytes)) !== expectedSha256.toLowerCase())
        throw new ModelError("model checksum mismatch");
    const spec = SCHEMA[kind];
    const session = await ort.InferenceSession.create(bytes, options);
    if (session.inputNames.length !== 1 || session.inputNames[0] !== spec.input || session.outputNames.length !== 1 || session.outputNames[0] !== spec.output)
        throw new ModelError("incompatible model schema");
    const run = async (input, rows, cols) => {
        if (cols !== spec.inWidth)
            throw new ModelError(`expected ${spec.inWidth} input columns`);
        const out = await session.run({ [spec.input]: new ort.Tensor("float32", input, [rows, cols]) });
        const t = out[spec.output];
        if (t.type !== "float32" || t.dims.length !== 2 || t.dims[0] !== rows || t.dims[1] !== spec.outWidth)
            throw new ModelError("incompatible model output");
        return t.data;
    };
    await run(new Float32Array(spec.inWidth), 1, spec.inWidth); // probe: validates tensor types and shapes
    return { run };
}
