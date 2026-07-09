/* @ts-self-types="./whitemagic_rust.d.ts" */

export class Coordinate5D {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        Coordinate5DFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_coordinate5d_free(ptr, 0);
    }
    /**
     * @returns {string}
     */
    get id() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.__wbg_get_coordinate5d_id(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {number}
     */
    get v() {
        const ret = wasm.__wbg_get_coordinate5d_v(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get w() {
        const ret = wasm.__wbg_get_coordinate5d_w(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get x() {
        const ret = wasm.__wbg_get_coordinate5d_x(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get y() {
        const ret = wasm.__wbg_get_coordinate5d_y(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get z() {
        const ret = wasm.__wbg_get_coordinate5d_z(this.__wbg_ptr);
        return ret;
    }
    /**
     * @param {string} arg0
     */
    set id(arg0) {
        const ptr0 = passStringToWasm0(arg0, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.__wbg_set_coordinate5d_id(this.__wbg_ptr, ptr0, len0);
    }
    /**
     * @param {number} arg0
     */
    set v(arg0) {
        wasm.__wbg_set_coordinate5d_v(this.__wbg_ptr, arg0);
    }
    /**
     * @param {number} arg0
     */
    set w(arg0) {
        wasm.__wbg_set_coordinate5d_w(this.__wbg_ptr, arg0);
    }
    /**
     * @param {number} arg0
     */
    set x(arg0) {
        wasm.__wbg_set_coordinate5d_x(this.__wbg_ptr, arg0);
    }
    /**
     * @param {number} arg0
     */
    set y(arg0) {
        wasm.__wbg_set_coordinate5d_y(this.__wbg_ptr, arg0);
    }
    /**
     * @param {number} arg0
     */
    set z(arg0) {
        wasm.__wbg_set_coordinate5d_z(this.__wbg_ptr, arg0);
    }
}
if (Symbol.dispose) Coordinate5D.prototype[Symbol.dispose] = Coordinate5D.prototype.free;

/**
 * Dharma rule engine for browser-local governance.
 */
export class DharmaEngine {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        DharmaEngineFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_dharmaengine_free(ptr, 0);
    }
    /**
     * @param {DharmaRule} rule
     */
    add_rule(rule) {
        _assertClass(rule, DharmaRule);
        var ptr0 = rule.__destroy_into_raw();
        wasm.dharmaengine_add_rule(this.__wbg_ptr, ptr0);
    }
    /**
     * Evaluate input text against all rules.
     * @param {string} text
     * @returns {DharmaResult}
     */
    evaluate(text) {
        const ptr0 = passStringToWasm0(text, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.dharmaengine_evaluate(this.__wbg_ptr, ptr0, len0);
        return DharmaResult.__wrap(ret);
    }
    /**
     * List all rule IDs as JSON array.
     * @returns {string}
     */
    list_rules() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.dharmaengine_list_rules(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    constructor() {
        const ret = wasm.dharmaengine_new();
        this.__wbg_ptr = ret >>> 0;
        DharmaEngineFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * @param {string} id
     * @returns {boolean}
     */
    remove_rule(id) {
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.dharmaengine_remove_rule(this.__wbg_ptr, ptr0, len0);
        return ret !== 0;
    }
    /**
     * @returns {number}
     */
    rule_count() {
        const ret = wasm.dharmaengine_rule_count(this.__wbg_ptr);
        return ret >>> 0;
    }
}
if (Symbol.dispose) DharmaEngine.prototype[Symbol.dispose] = DharmaEngine.prototype.free;

/**
 * Dharma evaluation result.
 */
export class DharmaResult {
    static __wrap(ptr) {
        ptr = ptr >>> 0;
        const obj = Object.create(DharmaResult.prototype);
        obj.__wbg_ptr = ptr;
        DharmaResultFinalization.register(obj, obj.__wbg_ptr, obj);
        return obj;
    }
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        DharmaResultFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_dharmaresult_free(ptr, 0);
    }
    /**
     * @returns {boolean}
     */
    get allowed() {
        const ret = wasm.dharmaresult_allowed(this.__wbg_ptr);
        return ret !== 0;
    }
    /**
     * @returns {number}
     */
    get evaluated_rules() {
        const ret = wasm.dharmaresult_evaluated_rules(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * @returns {string}
     */
    get matched_rule() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.dharmaresult_matched_rule(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    get message() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.dharmaresult_message(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
}
if (Symbol.dispose) DharmaResult.prototype[Symbol.dispose] = DharmaResult.prototype.free;

/**
 * A Dharma rule for content governance.
 */
export class DharmaRule {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        DharmaRuleFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_dharmarule_free(ptr, 0);
    }
    /**
     * @returns {string}
     */
    get action() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.dharmarule_action(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    get id() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.dharmarule_id(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    get message() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.dharmarule_message(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @param {string} id
     * @param {string} pattern
     * @param {string} action
     * @param {string} message
     */
    constructor(id, pattern, action, message) {
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ptr1 = passStringToWasm0(pattern, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len1 = WASM_VECTOR_LEN;
        const ptr2 = passStringToWasm0(action, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len2 = WASM_VECTOR_LEN;
        const ptr3 = passStringToWasm0(message, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len3 = WASM_VECTOR_LEN;
        const ret = wasm.dharmarule_new(ptr0, len0, ptr1, len1, ptr2, len2, ptr3, len3);
        this.__wbg_ptr = ret >>> 0;
        DharmaRuleFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * @returns {string}
     */
    get pattern() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.dharmarule_pattern(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
}
if (Symbol.dispose) DharmaRule.prototype[Symbol.dispose] = DharmaRule.prototype.free;

/**
 * Edge inference engine - WASM version
 */
export class EdgeEngine {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        EdgeEngineFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_edgeengine_free(ptr, 0);
    }
    /**
     * Add a rule to the engine
     * @param {EdgeRule} rule
     */
    add_rule(rule) {
        _assertClass(rule, EdgeRule);
        var ptr0 = rule.__destroy_into_raw();
        wasm.edgeengine_add_rule(this.__wbg_ptr, ptr0);
    }
    /**
     * Get statistics
     * @returns {string}
     */
    get_stats() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.edgeengine_get_stats(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Run inference on a query
     * @param {string} query
     * @returns {InferenceResult}
     */
    infer(query) {
        const ptr0 = passStringToWasm0(query, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.edgeengine_infer(this.__wbg_ptr, ptr0, len0);
        return InferenceResult.__wrap(ret);
    }
    /**
     * Get local resolution rate
     * @returns {number}
     */
    local_rate() {
        const ret = wasm.edgeengine_local_rate(this.__wbg_ptr);
        return ret;
    }
    constructor() {
        const ret = wasm.edgeengine_new();
        this.__wbg_ptr = ret >>> 0;
        EdgeEngineFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * Reset statistics
     */
    reset_stats() {
        wasm.edgeengine_reset_stats(this.__wbg_ptr);
    }
    /**
     * Get total tokens saved
     * @returns {number}
     */
    tokens_saved() {
        const ret = wasm.edgeengine_tokens_saved(this.__wbg_ptr);
        return ret >>> 0;
    }
}
if (Symbol.dispose) EdgeEngine.prototype[Symbol.dispose] = EdgeEngine.prototype.free;

/**
 * Edge inference rule
 */
export class EdgeRule {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        EdgeRuleFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_edgerule_free(ptr, 0);
    }
    /**
     * @returns {number}
     */
    get confidence() {
        const ret = wasm.edgerule_confidence(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {string}
     */
    get id() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.edgerule_id(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @param {string} id
     * @param {string} pattern
     * @param {string} response
     * @param {number} confidence
     */
    constructor(id, pattern, response, confidence) {
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ptr1 = passStringToWasm0(pattern, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len1 = WASM_VECTOR_LEN;
        const ptr2 = passStringToWasm0(response, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len2 = WASM_VECTOR_LEN;
        const ret = wasm.edgerule_new(ptr0, len0, ptr1, len1, ptr2, len2, confidence);
        this.__wbg_ptr = ret >>> 0;
        EdgeRuleFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * @returns {string}
     */
    get response() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.edgerule_response(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
}
if (Symbol.dispose) EdgeRule.prototype[Symbol.dispose] = EdgeRule.prototype.free;

/**
 * Gnosis snapshot — system self-awareness summary.
 */
export class GnosisSnapshot {
    static __wrap(ptr) {
        ptr = ptr >>> 0;
        const obj = Object.create(GnosisSnapshot.prototype);
        obj.__wbg_ptr = ptr;
        GnosisSnapshotFinalization.register(obj, obj.__wbg_ptr, obj);
        return obj;
    }
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        GnosisSnapshotFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_gnosissnapshot_free(ptr, 0);
    }
    /**
     * @returns {number}
     */
    get dharma_rules() {
        const ret = wasm.gnosissnapshot_dharma_rules(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * @returns {number}
     */
    get edge_local() {
        const ret = wasm.gnosissnapshot_edge_local(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * @returns {number}
     */
    get edge_queries() {
        const ret = wasm.gnosissnapshot_edge_queries(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * @returns {number}
     */
    get edge_tokens_saved() {
        const ret = wasm.gnosissnapshot_edge_tokens_saved(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * @returns {number}
     */
    get karma_balance() {
        const ret = wasm.gnosissnapshot_karma_balance(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get karma_entries() {
        const ret = wasm.gnosissnapshot_karma_entries(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * @returns {number}
     */
    get memory_count() {
        const ret = wasm.gnosissnapshot_memory_count(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * Serialize to JSON.
     * @returns {string}
     */
    to_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.gnosissnapshot_to_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
}
if (Symbol.dispose) GnosisSnapshot.prototype[Symbol.dispose] = GnosisSnapshot.prototype.free;

export class HolographicCoordinate {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        HolographicCoordinateFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_holographiccoordinate_free(ptr, 0);
    }
    /**
     * @returns {number}
     */
    get w() {
        const ret = wasm.__wbg_get_holographiccoordinate_w(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get x() {
        const ret = wasm.__wbg_get_holographiccoordinate_x(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get y() {
        const ret = wasm.__wbg_get_holographiccoordinate_y(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {number}
     */
    get z() {
        const ret = wasm.__wbg_get_holographiccoordinate_z(this.__wbg_ptr);
        return ret;
    }
    /**
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @param {number} w
     */
    constructor(x, y, z, w) {
        const ret = wasm.holographiccoordinate_new(x, y, z, w);
        this.__wbg_ptr = ret >>> 0;
        HolographicCoordinateFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * @returns {Float64Array}
     */
    to_vec() {
        const ret = wasm.holographiccoordinate_to_vec(this.__wbg_ptr);
        var v1 = getArrayF64FromWasm0(ret[0], ret[1]).slice();
        wasm.__wbindgen_free(ret[0], ret[1] * 8, 8);
        return v1;
    }
    /**
     * @param {number} arg0
     */
    set w(arg0) {
        wasm.__wbg_set_holographiccoordinate_w(this.__wbg_ptr, arg0);
    }
    /**
     * @param {number} arg0
     */
    set x(arg0) {
        wasm.__wbg_set_holographiccoordinate_x(this.__wbg_ptr, arg0);
    }
    /**
     * @param {number} arg0
     */
    set y(arg0) {
        wasm.__wbg_set_holographiccoordinate_y(this.__wbg_ptr, arg0);
    }
    /**
     * @param {number} arg0
     */
    set z(arg0) {
        wasm.__wbg_set_holographiccoordinate_z(this.__wbg_ptr, arg0);
    }
}
if (Symbol.dispose) HolographicCoordinate.prototype[Symbol.dispose] = HolographicCoordinate.prototype.free;

export class HolographicIndex {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        HolographicIndexFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_holographicindex_free(ptr, 0);
    }
    /**
     * @param {string} memory_id
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @param {number} w
     */
    add(memory_id, x, y, z, w) {
        const ptr0 = passStringToWasm0(memory_id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.holographicindex_add(this.__wbg_ptr, ptr0, len0, x, y, z, w);
    }
    constructor() {
        const ret = wasm.holographicindex_new();
        this.__wbg_ptr = ret >>> 0;
        HolographicIndexFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @param {number} w
     * @param {number} n
     * @returns {string}
     */
    query_nearest(x, y, z, w, n) {
        let deferred2_0;
        let deferred2_1;
        try {
            const ret = wasm.holographicindex_query_nearest(this.__wbg_ptr, x, y, z, w, n);
            var ptr1 = ret[0];
            var len1 = ret[1];
            if (ret[3]) {
                ptr1 = 0; len1 = 0;
                throw takeFromExternrefTable0(ret[2]);
            }
            deferred2_0 = ptr1;
            deferred2_1 = len1;
            return getStringFromWasm0(ptr1, len1);
        } finally {
            wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
        }
    }
}
if (Symbol.dispose) HolographicIndex.prototype[Symbol.dispose] = HolographicIndex.prototype.free;

export class HolographicIndexBasic {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        HolographicIndexBasicFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_holographicindexbasic_free(ptr, 0);
    }
    /**
     * @param {string} id
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @param {number} w
     */
    add(id, x, y, z, w) {
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.holographicindexbasic_add(this.__wbg_ptr, ptr0, len0, x, y, z, w);
    }
    constructor() {
        const ret = wasm.holographicindexbasic_new();
        this.__wbg_ptr = ret >>> 0;
        HolographicIndexBasicFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * @param {number} x
     * @param {number} y
     * @param {number} z
     * @param {number} w
     * @param {number} k
     * @returns {string}
     */
    query_nearest(x, y, z, w, k) {
        let deferred2_0;
        let deferred2_1;
        try {
            const ret = wasm.holographicindexbasic_query_nearest(this.__wbg_ptr, x, y, z, w, k);
            var ptr1 = ret[0];
            var len1 = ret[1];
            if (ret[3]) {
                ptr1 = 0; len1 = 0;
                throw takeFromExternrefTable0(ret[2]);
            }
            deferred2_0 = ptr1;
            deferred2_1 = len1;
            return getStringFromWasm0(ptr1, len1);
        } finally {
            wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
        }
    }
}
if (Symbol.dispose) HolographicIndexBasic.prototype[Symbol.dispose] = HolographicIndexBasic.prototype.free;

/**
 * Inference result
 */
export class InferenceResult {
    static __wrap(ptr) {
        ptr = ptr >>> 0;
        const obj = Object.create(InferenceResult.prototype);
        obj.__wbg_ptr = ptr;
        InferenceResultFinalization.register(obj, obj.__wbg_ptr, obj);
        return obj;
    }
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        InferenceResultFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_inferenceresult_free(ptr, 0);
    }
    /**
     * @returns {string}
     */
    get answer() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.inferenceresult_answer(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {number}
     */
    get confidence() {
        const ret = wasm.inferenceresult_confidence(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {string}
     */
    get method() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.inferenceresult_method(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {boolean}
     */
    get needs_cloud() {
        const ret = wasm.inferenceresult_needs_cloud(this.__wbg_ptr);
        return ret !== 0;
    }
    /**
     * @returns {number}
     */
    get tokens_saved() {
        const ret = wasm.inferenceresult_tokens_saved(this.__wbg_ptr);
        return ret >>> 0;
    }
}
if (Symbol.dispose) InferenceResult.prototype[Symbol.dispose] = InferenceResult.prototype.free;

/**
 * A karma ledger entry.
 */
export class KarmaEntry {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        KarmaEntryFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_karmaentry_free(ptr, 0);
    }
    /**
     * @returns {string}
     */
    get action() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.karmaentry_action(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {number}
     */
    get delta() {
        const ret = wasm.karmaentry_delta(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {string}
     */
    get description() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.karmaentry_description(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    get id() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.karmaentry_id(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    get timestamp() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.karmaentry_timestamp(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
}
if (Symbol.dispose) KarmaEntry.prototype[Symbol.dispose] = KarmaEntry.prototype.free;

/**
 * Append-only karma ledger.
 */
export class KarmaLedger {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        KarmaLedgerFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_karmaledger_free(ptr, 0);
    }
    /**
     * Get current karma balance.
     * @returns {number}
     */
    balance() {
        const ret = wasm.karmaledger_balance(this.__wbg_ptr);
        return ret;
    }
    /**
     * Get total number of entries.
     * @returns {number}
     */
    count() {
        const ret = wasm.karmaledger_count(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * Export all entries as JSON (for backup).
     * @returns {string}
     */
    export_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.karmaledger_export_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    constructor() {
        const ret = wasm.karmaledger_new();
        this.__wbg_ptr = ret >>> 0;
        KarmaLedgerFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * Get recent entries as JSON (last N entries).
     * @param {number} n
     * @returns {string}
     */
    recent_json(n) {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.karmaledger_recent_json(this.__wbg_ptr, n);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Record a karma action. Returns the entry ID.
     * @param {string} action
     * @param {number} delta
     * @param {string} description
     * @returns {string}
     */
    record(action, delta, description) {
        let deferred3_0;
        let deferred3_1;
        try {
            const ptr0 = passStringToWasm0(action, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len0 = WASM_VECTOR_LEN;
            const ptr1 = passStringToWasm0(description, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len1 = WASM_VECTOR_LEN;
            const ret = wasm.karmaledger_record(this.__wbg_ptr, ptr0, len0, delta, ptr1, len1);
            deferred3_0 = ret[0];
            deferred3_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
        }
    }
}
if (Symbol.dispose) KarmaLedger.prototype[Symbol.dispose] = KarmaLedger.prototype.free;

/**
 * In-browser memory store (HashMap-backed cache + IndexedDB persistence).
 */
export class MemoryStore {
    static __wrap(ptr) {
        ptr = ptr >>> 0;
        const obj = Object.create(MemoryStore.prototype);
        obj.__wbg_ptr = ptr;
        MemoryStoreFinalization.register(obj, obj.__wbg_ptr, obj);
        return obj;
    }
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        MemoryStoreFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_memorystore_free(ptr, 0);
    }
    /**
     * Get count of stored memories.
     * @returns {number}
     */
    count() {
        const ret = wasm.memorystore_count(this.__wbg_ptr);
        return ret >>> 0;
    }
    /**
     * Create a new memory. Returns the assigned ID.
     * @param {string} title
     * @param {string} content
     * @param {string} tags_json
     * @returns {string}
     */
    create(title, content, tags_json) {
        let deferred4_0;
        let deferred4_1;
        try {
            const ptr0 = passStringToWasm0(title, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len0 = WASM_VECTOR_LEN;
            const ptr1 = passStringToWasm0(content, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len1 = WASM_VECTOR_LEN;
            const ptr2 = passStringToWasm0(tags_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len2 = WASM_VECTOR_LEN;
            const ret = wasm.memorystore_create(this.__wbg_ptr, ptr0, len0, ptr1, len1, ptr2, len2);
            deferred4_0 = ret[0];
            deferred4_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred4_0, deferred4_1, 1);
        }
    }
    /**
     * Get the IndexedDB database name.
     * @returns {string}
     */
    get db_name() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.memorystore_db_name(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Delete a memory by ID.
     * @param {string} id
     * @returns {boolean}
     */
    delete(id) {
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.memorystore_delete(this.__wbg_ptr, ptr0, len0);
        return ret !== 0;
    }
    /**
     * Delete a single memory from IndexedDB.
     * @param {string} id
     * @returns {Promise<boolean>}
     */
    delete_persisted(id) {
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.memorystore_delete_persisted(this.__wbg_ptr, ptr0, len0);
        return ret;
    }
    /**
     * Export all memories as a JSON array (for backup/transfer).
     * @returns {string}
     */
    export_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.memorystore_export_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Hydrate the in-memory cache from IndexedDB.
     * @returns {Promise<number>}
     */
    hydrate() {
        const ret = wasm.memorystore_hydrate(this.__wbg_ptr);
        return ret;
    }
    /**
     * Import memories from a JSON array (merge into store).
     * Returns count of memories imported.
     * @param {string} json_str
     * @returns {number}
     */
    import_json(json_str) {
        const ptr0 = passStringToWasm0(json_str, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.memorystore_import_json(this.__wbg_ptr, ptr0, len0);
        return ret >>> 0;
    }
    /**
     * List all memories, sorted by importance (descending).
     * @returns {string}
     */
    list() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.memorystore_list(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    constructor() {
        const ret = wasm.memorystore_new();
        this.__wbg_ptr = ret >>> 0;
        MemoryStoreFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * Persist all memories to IndexedDB (full sync).
     * @returns {Promise<number>}
     */
    persist() {
        const ret = wasm.memorystore_persist(this.__wbg_ptr);
        return ret;
    }
    /**
     * Persist a single memory to IndexedDB.
     * @param {string} id
     * @returns {Promise<boolean>}
     */
    persist_one(id) {
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.memorystore_persist_one(this.__wbg_ptr, ptr0, len0);
        return ret;
    }
    /**
     * Read a memory by ID. Returns JSON or empty string if not found.
     * @param {string} id
     * @returns {string}
     */
    read(id) {
        let deferred2_0;
        let deferred2_1;
        try {
            const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len0 = WASM_VECTOR_LEN;
            const ret = wasm.memorystore_read(this.__wbg_ptr, ptr0, len0);
            deferred2_0 = ret[0];
            deferred2_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
        }
    }
    /**
     * Full-text search across title and content. Returns JSON array of memory IDs.
     * @param {string} query
     * @returns {string}
     */
    search(query) {
        let deferred2_0;
        let deferred2_1;
        try {
            const ptr0 = passStringToWasm0(query, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len0 = WASM_VECTOR_LEN;
            const ret = wasm.memorystore_search(this.__wbg_ptr, ptr0, len0);
            deferred2_0 = ret[0];
            deferred2_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
        }
    }
    /**
     * Search by tag. Returns JSON array of memory IDs.
     * @param {string} tag
     * @returns {string}
     */
    search_by_tag(tag) {
        let deferred2_0;
        let deferred2_1;
        try {
            const ptr0 = passStringToWasm0(tag, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len0 = WASM_VECTOR_LEN;
            const ret = wasm.memorystore_search_by_tag(this.__wbg_ptr, ptr0, len0);
            deferred2_0 = ret[0];
            deferred2_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
        }
    }
    /**
     * Update a memory's content and/or title.
     * @param {string} id
     * @param {string} title
     * @param {string} content
     * @returns {boolean}
     */
    update(id, title, content) {
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ptr1 = passStringToWasm0(title, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len1 = WASM_VECTOR_LEN;
        const ptr2 = passStringToWasm0(content, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len2 = WASM_VECTOR_LEN;
        const ret = wasm.memorystore_update(this.__wbg_ptr, ptr0, len0, ptr1, len1, ptr2, len2);
        return ret !== 0;
    }
    /**
     * Create a MemoryStore with a custom IndexedDB database name
     * (useful for multi-user isolation).
     * @param {string} db_name
     * @returns {MemoryStore}
     */
    static with_db_name(db_name) {
        const ptr0 = passStringToWasm0(db_name, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.memorystore_with_db_name(ptr0, len0);
        return MemoryStore.__wrap(ret);
    }
}
if (Symbol.dispose) MemoryStore.prototype[Symbol.dispose] = MemoryStore.prototype.free;

/**
 * A memory record stored in the browser.
 */
export class WasmMemory {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        WasmMemoryFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_wasmmemory_free(ptr, 0);
    }
    /**
     * @param {string} tag
     */
    add_tag(tag) {
        const ptr0 = passStringToWasm0(tag, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.wasmmemory_add_tag(this.__wbg_ptr, ptr0, len0);
    }
    /**
     * @returns {string}
     */
    get content() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.wasmmemory_content(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    get created_at() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.wasmmemory_created_at(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    get id() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.wasmmemory_id(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {number}
     */
    get importance() {
        const ret = wasm.wasmmemory_importance(this.__wbg_ptr);
        return ret;
    }
    /**
     * @returns {string}
     */
    get memory_type() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.wasmmemory_memory_type(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @param {string} id
     * @param {string} title
     * @param {string} content
     */
    constructor(id, title, content) {
        const ptr0 = passStringToWasm0(id, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ptr1 = passStringToWasm0(title, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len1 = WASM_VECTOR_LEN;
        const ptr2 = passStringToWasm0(content, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len2 = WASM_VECTOR_LEN;
        const ret = wasm.wasmmemory_new(ptr0, len0, ptr1, len1, ptr2, len2);
        this.__wbg_ptr = ret >>> 0;
        WasmMemoryFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * @param {string} tag
     */
    remove_tag(tag) {
        const ptr0 = passStringToWasm0(tag, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.wasmmemory_remove_tag(this.__wbg_ptr, ptr0, len0);
    }
    /**
     * @param {string} v
     */
    set content(v) {
        const ptr0 = passStringToWasm0(v, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.wasmmemory_set_content(this.__wbg_ptr, ptr0, len0);
    }
    /**
     * @param {number} v
     */
    set importance(v) {
        wasm.wasmmemory_set_importance(this.__wbg_ptr, v);
    }
    /**
     * @param {string} v
     */
    set title(v) {
        const ptr0 = passStringToWasm0(v, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        wasm.wasmmemory_set_title(this.__wbg_ptr, ptr0, len0);
    }
    /**
     * @returns {string}
     */
    tags_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.wasmmemory_tags_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    get title() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.wasmmemory_title(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    to_json() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.wasmmemory_to_json(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * @returns {string}
     */
    get updated_at() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.wasmmemory_updated_at(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
}
if (Symbol.dispose) WasmMemory.prototype[Symbol.dispose] = WasmMemory.prototype.free;

/**
 * Batch cosine similarity: compare one query vector against many candidates.
 * Returns JSON array of {index, score} sorted by score descending.
 * @param {string} query_json
 * @param {string} candidates_json
 * @param {number} top_k
 * @returns {string}
 */
export function batch_similarity(query_json, candidates_json, top_k) {
    let deferred3_0;
    let deferred3_1;
    try {
        const ptr0 = passStringToWasm0(query_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ptr1 = passStringToWasm0(candidates_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len1 = WASM_VECTOR_LEN;
        const ret = wasm.batch_similarity(ptr0, len0, ptr1, len1, top_k);
        deferred3_0 = ret[0];
        deferred3_1 = ret[1];
        return getStringFromWasm0(ret[0], ret[1]);
    } finally {
        wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
    }
}

/**
 * Cosine similarity between two vectors (passed as JSON arrays)
 * @param {string} a_json
 * @param {string} b_json
 * @returns {number}
 */
export function cosine_similarity(a_json, b_json) {
    const ptr0 = passStringToWasm0(a_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len0 = WASM_VECTOR_LEN;
    const ptr1 = passStringToWasm0(b_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len1 = WASM_VECTOR_LEN;
    const ret = wasm.cosine_similarity(ptr0, len0, ptr1, len1);
    return ret;
}

/**
 * @param {Float32Array} embeddings_flat
 * @param {number} embedding_dim
 * @param {number} threshold
 * @param {number} max_results
 * @returns {string}
 */
export function embedding_minhash_find_duplicates(embeddings_flat, embedding_dim, threshold, max_results) {
    let deferred3_0;
    let deferred3_1;
    try {
        const ptr0 = passArrayF32ToWasm0(embeddings_flat, wasm.__wbindgen_malloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.embedding_minhash_find_duplicates(ptr0, len0, embedding_dim, threshold, max_results);
        var ptr2 = ret[0];
        var len2 = ret[1];
        if (ret[3]) {
            ptr2 = 0; len2 = 0;
            throw takeFromExternrefTable0(ret[2]);
        }
        deferred3_0 = ptr2;
        deferred3_1 = len2;
        return getStringFromWasm0(ptr2, len2);
    } finally {
        wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
    }
}

/**
 * Generate a Gnosis snapshot from the current system state.
 * @param {MemoryStore} store
 * @param {KarmaLedger} karma
 * @param {DharmaEngine} dharma
 * @param {EdgeEngine} engine
 * @returns {GnosisSnapshot}
 */
export function gnosis_snapshot(store, karma, dharma, engine) {
    _assertClass(store, MemoryStore);
    _assertClass(karma, KarmaLedger);
    _assertClass(dharma, DharmaEngine);
    _assertClass(engine, EdgeEngine);
    const ret = wasm.gnosis_snapshot(store.__wbg_ptr, karma.__wbg_ptr, dharma.__wbg_ptr, engine.__wbg_ptr);
    return GnosisSnapshot.__wrap(ret);
}

/**
 * @param {string} memories_json
 * @returns {string}
 */
export function holographic_encode_batch(memories_json) {
    let deferred3_0;
    let deferred3_1;
    try {
        const ptr0 = passStringToWasm0(memories_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.holographic_encode_batch(ptr0, len0);
        var ptr2 = ret[0];
        var len2 = ret[1];
        if (ret[3]) {
            ptr2 = 0; len2 = 0;
            throw takeFromExternrefTable0(ret[2]);
        }
        deferred3_0 = ptr2;
        deferred3_1 = len2;
        return getStringFromWasm0(ptr2, len2);
    } finally {
        wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
    }
}

/**
 * @param {string} memory_json
 * @returns {string}
 */
export function holographic_encode_single(memory_json) {
    let deferred3_0;
    let deferred3_1;
    try {
        const ptr0 = passStringToWasm0(memory_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.holographic_encode_single(ptr0, len0);
        var ptr2 = ret[0];
        var len2 = ret[1];
        if (ret[3]) {
            ptr2 = 0; len2 = 0;
            throw takeFromExternrefTable0(ret[2]);
        }
        deferred3_0 = ptr2;
        deferred3_1 = len2;
        return getStringFromWasm0(ptr2, len2);
    } finally {
        wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
    }
}

/**
 * Initialize the WASM module — call once on startup.
 * Installs the panic hook for better error messages.
 */
export function init_wasm() {
    wasm.init_wasm();
}

export function main_js() {
    wasm.main_js();
}

/**
 * @param {string} keywords_json
 * @param {number} threshold
 * @param {number} max_results
 * @returns {string}
 */
export function minhash_find_duplicates(keywords_json, threshold, max_results) {
    let deferred3_0;
    let deferred3_1;
    try {
        const ptr0 = passStringToWasm0(keywords_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.minhash_find_duplicates(ptr0, len0, threshold, max_results);
        var ptr2 = ret[0];
        var len2 = ret[1];
        if (ret[3]) {
            ptr2 = 0; len2 = 0;
            throw takeFromExternrefTable0(ret[2]);
        }
        deferred3_0 = ptr2;
        deferred3_1 = len2;
        return getStringFromWasm0(ptr2, len2);
    } finally {
        wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
    }
}

/**
 * @param {string} keywords_json
 * @returns {string}
 */
export function minhash_signatures(keywords_json) {
    let deferred3_0;
    let deferred3_1;
    try {
        const ptr0 = passStringToWasm0(keywords_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.minhash_signatures(ptr0, len0);
        var ptr2 = ret[0];
        var len2 = ret[1];
        if (ret[3]) {
            ptr2 = 0; len2 = 0;
            throw takeFromExternrefTable0(ret[2]);
        }
        deferred3_0 = ptr2;
        deferred3_1 = len2;
        return getStringFromWasm0(ptr2, len2);
    } finally {
        wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
    }
}

/**
 * Quick inference function (convenience)
 * @param {string} query
 * @returns {string}
 */
export function quick_infer(query) {
    let deferred2_0;
    let deferred2_1;
    try {
        const ptr0 = passStringToWasm0(query, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.quick_infer(ptr0, len0);
        deferred2_0 = ret[0];
        deferred2_1 = ret[1];
        return getStringFromWasm0(ret[0], ret[1]);
    } finally {
        wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
    }
}

/**
 * Full-text search: find substring matches in a list of texts.
 * Returns JSON array of matching indices.
 * @param {string} query
 * @param {string} texts_json
 * @returns {string}
 */
export function text_search(query, texts_json) {
    let deferred3_0;
    let deferred3_1;
    try {
        const ptr0 = passStringToWasm0(query, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ptr1 = passStringToWasm0(texts_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len1 = WASM_VECTOR_LEN;
        const ret = wasm.text_search(ptr0, len0, ptr1, len1);
        deferred3_0 = ret[0];
        deferred3_1 = ret[1];
        return getStringFromWasm0(ret[0], ret[1]);
    } finally {
        wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
    }
}

/**
 * Check if WASM module is loaded
 * @returns {boolean}
 */
export function wasm_ready() {
    const ret = wasm.wasm_ready();
    return ret !== 0;
}

/**
 * Get WASM version
 * @returns {string}
 */
export function wasm_version() {
    let deferred1_0;
    let deferred1_1;
    try {
        const ret = wasm.wasm_version();
        deferred1_0 = ret[0];
        deferred1_1 = ret[1];
        return getStringFromWasm0(ret[0], ret[1]);
    } finally {
        wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
    }
}
function __wbg_get_imports() {
    const import0 = {
        __proto__: null,
        __wbg___wbindgen_is_function_3baa9db1a987f47d: function(arg0) {
            const ret = typeof(arg0) === 'function';
            return ret;
        },
        __wbg___wbindgen_is_undefined_29a43b4d42920abd: function(arg0) {
            const ret = arg0 === undefined;
            return ret;
        },
        __wbg___wbindgen_string_get_7ed5322991caaec5: function(arg0, arg1) {
            const obj = arg1;
            const ret = typeof(obj) === 'string' ? obj : undefined;
            var ptr1 = isLikeNone(ret) ? 0 : passStringToWasm0(ret, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            var len1 = WASM_VECTOR_LEN;
            getDataViewMemory0().setInt32(arg0 + 4 * 1, len1, true);
            getDataViewMemory0().setInt32(arg0 + 4 * 0, ptr1, true);
        },
        __wbg___wbindgen_throw_6b64449b9b9ed33c: function(arg0, arg1) {
            throw new Error(getStringFromWasm0(arg0, arg1));
        },
        __wbg__wbg_cb_unref_b46c9b5a9f08ec37: function(arg0) {
            arg0._wbg_cb_unref();
        },
        __wbg_call_a24592a6f349a97e: function() { return handleError(function (arg0, arg1, arg2) {
            const ret = arg0.call(arg1, arg2);
            return ret;
        }, arguments); },
        __wbg_clear_e20ff80e7eda7707: function() { return handleError(function (arg0) {
            const ret = arg0.clear();
            return ret;
        }, arguments); },
        __wbg_close_a7d2c11ae747c112: function(arg0) {
            arg0.close();
        },
        __wbg_contains_f911f9ff03e5a433: function(arg0, arg1, arg2) {
            const ret = arg0.contains(getStringFromWasm0(arg1, arg2));
            return ret;
        },
        __wbg_createObjectStore_fda2c8d772b080f5: function() { return handleError(function (arg0, arg1, arg2) {
            const ret = arg0.createObjectStore(getStringFromWasm0(arg1, arg2));
            return ret;
        }, arguments); },
        __wbg_delete_10b3489d089185d7: function() { return handleError(function (arg0, arg1) {
            const ret = arg0.delete(arg1);
            return ret;
        }, arguments); },
        __wbg_error_a6fa202b58aa1cd3: function(arg0, arg1) {
            let deferred0_0;
            let deferred0_1;
            try {
                deferred0_0 = arg0;
                deferred0_1 = arg1;
                console.error(getStringFromWasm0(arg0, arg1));
            } finally {
                wasm.__wbindgen_free(deferred0_0, deferred0_1, 1);
            }
        },
        __wbg_getAll_a898878594f5e590: function() { return handleError(function (arg0) {
            const ret = arg0.getAll();
            return ret;
        }, arguments); },
        __wbg_get_8360291721e2339f: function(arg0, arg1) {
            const ret = arg0[arg1 >>> 0];
            return ret;
        },
        __wbg_indexedDB_ac4afadd7c87762a: function() { return handleError(function (arg0) {
            const ret = arg0.indexedDB;
            return isLikeNone(ret) ? 0 : addToExternrefTable0(ret);
        }, arguments); },
        __wbg_instanceof_Promise_78658358a9b27cd4: function(arg0) {
            let result;
            try {
                result = arg0 instanceof Promise;
            } catch (_) {
                result = false;
            }
            const ret = result;
            return ret;
        },
        __wbg_instanceof_Window_cc64c86c8ef9e02b: function(arg0) {
            let result;
            try {
                result = arg0 instanceof Window;
            } catch (_) {
                result = false;
            }
            const ret = result;
            return ret;
        },
        __wbg_length_3d4ecd04bd8d22f1: function(arg0) {
            const ret = arg0.length;
            return ret;
        },
        __wbg_new_227d7c05414eb861: function() {
            const ret = new Error();
            return ret;
        },
        __wbg_new_7913666fe5070684: function(arg0) {
            const ret = new Date(arg0);
            return ret;
        },
        __wbg_new_typed_323f37fd55ab048d: function(arg0, arg1) {
            try {
                var state0 = {a: arg0, b: arg1};
                var cb0 = (arg0, arg1) => {
                    const a = state0.a;
                    state0.a = 0;
                    try {
                        return wasm_bindgen__convert__closures_____invoke__h0ca18a6293b4ae72(a, state0.b, arg0, arg1);
                    } finally {
                        state0.a = a;
                    }
                };
                const ret = new Promise(cb0);
                return ret;
            } finally {
                state0.a = 0;
            }
        },
        __wbg_new_with_args_57b505df22335acd: function(arg0, arg1, arg2, arg3) {
            const ret = new Function(getStringFromWasm0(arg0, arg1), getStringFromWasm0(arg2, arg3));
            return ret;
        },
        __wbg_now_a9b7df1cbee90986: function() {
            const ret = Date.now();
            return ret;
        },
        __wbg_objectStoreNames_c755717c02e8876b: function(arg0) {
            const ret = arg0.objectStoreNames;
            return ret;
        },
        __wbg_objectStore_5942e8f91c946be8: function() { return handleError(function (arg0, arg1, arg2) {
            const ret = arg0.objectStore(getStringFromWasm0(arg1, arg2));
            return ret;
        }, arguments); },
        __wbg_open_0949b7cdde2ab99a: function() { return handleError(function (arg0, arg1, arg2) {
            const ret = arg0.open(getStringFromWasm0(arg1, arg2));
            return ret;
        }, arguments); },
        __wbg_put_fd02d3070a55994c: function() { return handleError(function (arg0, arg1, arg2) {
            const ret = arg0.put(arg1, arg2);
            return ret;
        }, arguments); },
        __wbg_queueMicrotask_5d15a957e6aa920e: function(arg0) {
            queueMicrotask(arg0);
        },
        __wbg_queueMicrotask_f8819e5ffc402f36: function(arg0) {
            const ret = arg0.queueMicrotask;
            return ret;
        },
        __wbg_reject_ef67a12c7cc1cf7c: function(arg0) {
            const ret = Promise.reject(arg0);
            return ret;
        },
        __wbg_resolve_e6c466bc1052f16c: function(arg0) {
            const ret = Promise.resolve(arg0);
            return ret;
        },
        __wbg_result_f782323755b96dc8: function() { return handleError(function (arg0) {
            const ret = arg0.result;
            return ret;
        }, arguments); },
        __wbg_set_onupgradeneeded_3fc8649a687213f5: function(arg0, arg1) {
            arg0.onupgradeneeded = arg1;
        },
        __wbg_stack_3b0d974bbf31e44f: function(arg0, arg1) {
            const ret = arg1.stack;
            const ptr1 = passStringToWasm0(ret, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len1 = WASM_VECTOR_LEN;
            getDataViewMemory0().setInt32(arg0 + 4 * 1, len1, true);
            getDataViewMemory0().setInt32(arg0 + 4 * 0, ptr1, true);
        },
        __wbg_static_accessor_GLOBAL_8cfadc87a297ca02: function() {
            const ret = typeof global === 'undefined' ? null : global;
            return isLikeNone(ret) ? 0 : addToExternrefTable0(ret);
        },
        __wbg_static_accessor_GLOBAL_THIS_602256ae5c8f42cf: function() {
            const ret = typeof globalThis === 'undefined' ? null : globalThis;
            return isLikeNone(ret) ? 0 : addToExternrefTable0(ret);
        },
        __wbg_static_accessor_SELF_e445c1c7484aecc3: function() {
            const ret = typeof self === 'undefined' ? null : self;
            return isLikeNone(ret) ? 0 : addToExternrefTable0(ret);
        },
        __wbg_static_accessor_WINDOW_f20e8576ef1e0f17: function() {
            const ret = typeof window === 'undefined' ? null : window;
            return isLikeNone(ret) ? 0 : addToExternrefTable0(ret);
        },
        __wbg_target_6d97e221d11b71b6: function(arg0) {
            const ret = arg0.target;
            return isLikeNone(ret) ? 0 : addToExternrefTable0(ret);
        },
        __wbg_then_792e0c862b060889: function(arg0, arg1, arg2) {
            const ret = arg0.then(arg1, arg2);
            return ret;
        },
        __wbg_then_8e16ee11f05e4827: function(arg0, arg1) {
            const ret = arg0.then(arg1);
            return ret;
        },
        __wbg_toISOString_07c00b3614e865a1: function(arg0) {
            const ret = arg0.toISOString();
            return ret;
        },
        __wbg_transaction_653efe7dcf307618: function() { return handleError(function (arg0, arg1, arg2, arg3) {
            const ret = arg0.transaction(getStringFromWasm0(arg1, arg2), __wbindgen_enum_IdbTransactionMode[arg3]);
            return ret;
        }, arguments); },
        __wbindgen_cast_0000000000000001: function(arg0, arg1) {
            // Cast intrinsic for `Closure(Closure { owned: true, function: Function { arguments: [Externref], shim_idx: 56, ret: Result(Unit), inner_ret: Some(Result(Unit)) }, mutable: true }) -> Externref`.
            const ret = makeMutClosure(arg0, arg1, wasm_bindgen__convert__closures_____invoke__hb240e798b97a84fa);
            return ret;
        },
        __wbindgen_cast_0000000000000002: function(arg0, arg1) {
            // Cast intrinsic for `Closure(Closure { owned: true, function: Function { arguments: [NamedExternref("IDBVersionChangeEvent")], shim_idx: 47, ret: Unit, inner_ret: Some(Unit) }, mutable: true }) -> Externref`.
            const ret = makeMutClosure(arg0, arg1, wasm_bindgen__convert__closures_____invoke__h85ded4be30241e32);
            return ret;
        },
        __wbindgen_cast_0000000000000003: function(arg0) {
            // Cast intrinsic for `F64 -> Externref`.
            const ret = arg0;
            return ret;
        },
        __wbindgen_cast_0000000000000004: function(arg0, arg1) {
            // Cast intrinsic for `Ref(String) -> Externref`.
            const ret = getStringFromWasm0(arg0, arg1);
            return ret;
        },
        __wbindgen_init_externref_table: function() {
            const table = wasm.__wbindgen_externrefs;
            const offset = table.grow(4);
            table.set(0, undefined);
            table.set(offset + 0, undefined);
            table.set(offset + 1, null);
            table.set(offset + 2, true);
            table.set(offset + 3, false);
        },
    };
    return {
        __proto__: null,
        "./whitemagic_rust_bg.js": import0,
    };
}

function wasm_bindgen__convert__closures_____invoke__h85ded4be30241e32(arg0, arg1, arg2) {
    wasm.wasm_bindgen__convert__closures_____invoke__h85ded4be30241e32(arg0, arg1, arg2);
}

function wasm_bindgen__convert__closures_____invoke__hb240e798b97a84fa(arg0, arg1, arg2) {
    const ret = wasm.wasm_bindgen__convert__closures_____invoke__hb240e798b97a84fa(arg0, arg1, arg2);
    if (ret[1]) {
        throw takeFromExternrefTable0(ret[0]);
    }
}

function wasm_bindgen__convert__closures_____invoke__h0ca18a6293b4ae72(arg0, arg1, arg2, arg3) {
    wasm.wasm_bindgen__convert__closures_____invoke__h0ca18a6293b4ae72(arg0, arg1, arg2, arg3);
}


const __wbindgen_enum_IdbTransactionMode = ["readonly", "readwrite", "versionchange", "readwriteflush", "cleanup"];
const Coordinate5DFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_coordinate5d_free(ptr >>> 0, 1));
const DharmaEngineFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_dharmaengine_free(ptr >>> 0, 1));
const DharmaResultFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_dharmaresult_free(ptr >>> 0, 1));
const DharmaRuleFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_dharmarule_free(ptr >>> 0, 1));
const EdgeEngineFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_edgeengine_free(ptr >>> 0, 1));
const EdgeRuleFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_edgerule_free(ptr >>> 0, 1));
const GnosisSnapshotFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_gnosissnapshot_free(ptr >>> 0, 1));
const HolographicCoordinateFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_holographiccoordinate_free(ptr >>> 0, 1));
const HolographicIndexFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_holographicindex_free(ptr >>> 0, 1));
const HolographicIndexBasicFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_holographicindexbasic_free(ptr >>> 0, 1));
const InferenceResultFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_inferenceresult_free(ptr >>> 0, 1));
const KarmaEntryFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_karmaentry_free(ptr >>> 0, 1));
const KarmaLedgerFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_karmaledger_free(ptr >>> 0, 1));
const MemoryStoreFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_memorystore_free(ptr >>> 0, 1));
const WasmMemoryFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_wasmmemory_free(ptr >>> 0, 1));

function addToExternrefTable0(obj) {
    const idx = wasm.__externref_table_alloc();
    wasm.__wbindgen_externrefs.set(idx, obj);
    return idx;
}

function _assertClass(instance, klass) {
    if (!(instance instanceof klass)) {
        throw new Error(`expected instance of ${klass.name}`);
    }
}

const CLOSURE_DTORS = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(state => wasm.__wbindgen_destroy_closure(state.a, state.b));

function getArrayF64FromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    return getFloat64ArrayMemory0().subarray(ptr / 8, ptr / 8 + len);
}

let cachedDataViewMemory0 = null;
function getDataViewMemory0() {
    if (cachedDataViewMemory0 === null || cachedDataViewMemory0.buffer.detached === true || (cachedDataViewMemory0.buffer.detached === undefined && cachedDataViewMemory0.buffer !== wasm.memory.buffer)) {
        cachedDataViewMemory0 = new DataView(wasm.memory.buffer);
    }
    return cachedDataViewMemory0;
}

let cachedFloat32ArrayMemory0 = null;
function getFloat32ArrayMemory0() {
    if (cachedFloat32ArrayMemory0 === null || cachedFloat32ArrayMemory0.byteLength === 0) {
        cachedFloat32ArrayMemory0 = new Float32Array(wasm.memory.buffer);
    }
    return cachedFloat32ArrayMemory0;
}

let cachedFloat64ArrayMemory0 = null;
function getFloat64ArrayMemory0() {
    if (cachedFloat64ArrayMemory0 === null || cachedFloat64ArrayMemory0.byteLength === 0) {
        cachedFloat64ArrayMemory0 = new Float64Array(wasm.memory.buffer);
    }
    return cachedFloat64ArrayMemory0;
}

function getStringFromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    return decodeText(ptr, len);
}

let cachedUint8ArrayMemory0 = null;
function getUint8ArrayMemory0() {
    if (cachedUint8ArrayMemory0 === null || cachedUint8ArrayMemory0.byteLength === 0) {
        cachedUint8ArrayMemory0 = new Uint8Array(wasm.memory.buffer);
    }
    return cachedUint8ArrayMemory0;
}

function handleError(f, args) {
    try {
        return f.apply(this, args);
    } catch (e) {
        const idx = addToExternrefTable0(e);
        wasm.__wbindgen_exn_store(idx);
    }
}

function isLikeNone(x) {
    return x === undefined || x === null;
}

function makeMutClosure(arg0, arg1, f) {
    const state = { a: arg0, b: arg1, cnt: 1 };
    const real = (...args) => {

        // First up with a closure we increment the internal reference
        // count. This ensures that the Rust closure environment won't
        // be deallocated while we're invoking it.
        state.cnt++;
        const a = state.a;
        state.a = 0;
        try {
            return f(a, state.b, ...args);
        } finally {
            state.a = a;
            real._wbg_cb_unref();
        }
    };
    real._wbg_cb_unref = () => {
        if (--state.cnt === 0) {
            wasm.__wbindgen_destroy_closure(state.a, state.b);
            state.a = 0;
            CLOSURE_DTORS.unregister(state);
        }
    };
    CLOSURE_DTORS.register(real, state, state);
    return real;
}

function passArrayF32ToWasm0(arg, malloc) {
    const ptr = malloc(arg.length * 4, 4) >>> 0;
    getFloat32ArrayMemory0().set(arg, ptr / 4);
    WASM_VECTOR_LEN = arg.length;
    return ptr;
}

function passStringToWasm0(arg, malloc, realloc) {
    if (realloc === undefined) {
        const buf = cachedTextEncoder.encode(arg);
        const ptr = malloc(buf.length, 1) >>> 0;
        getUint8ArrayMemory0().subarray(ptr, ptr + buf.length).set(buf);
        WASM_VECTOR_LEN = buf.length;
        return ptr;
    }

    let len = arg.length;
    let ptr = malloc(len, 1) >>> 0;

    const mem = getUint8ArrayMemory0();

    let offset = 0;

    for (; offset < len; offset++) {
        const code = arg.charCodeAt(offset);
        if (code > 0x7F) break;
        mem[ptr + offset] = code;
    }
    if (offset !== len) {
        if (offset !== 0) {
            arg = arg.slice(offset);
        }
        ptr = realloc(ptr, len, len = offset + arg.length * 3, 1) >>> 0;
        const view = getUint8ArrayMemory0().subarray(ptr + offset, ptr + len);
        const ret = cachedTextEncoder.encodeInto(arg, view);

        offset += ret.written;
        ptr = realloc(ptr, len, offset, 1) >>> 0;
    }

    WASM_VECTOR_LEN = offset;
    return ptr;
}

function takeFromExternrefTable0(idx) {
    const value = wasm.__wbindgen_externrefs.get(idx);
    wasm.__externref_table_dealloc(idx);
    return value;
}

let cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
cachedTextDecoder.decode();
const MAX_SAFARI_DECODE_BYTES = 2146435072;
let numBytesDecoded = 0;
function decodeText(ptr, len) {
    numBytesDecoded += len;
    if (numBytesDecoded >= MAX_SAFARI_DECODE_BYTES) {
        cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
        cachedTextDecoder.decode();
        numBytesDecoded = len;
    }
    return cachedTextDecoder.decode(getUint8ArrayMemory0().subarray(ptr, ptr + len));
}

const cachedTextEncoder = new TextEncoder();

if (!('encodeInto' in cachedTextEncoder)) {
    cachedTextEncoder.encodeInto = function (arg, view) {
        const buf = cachedTextEncoder.encode(arg);
        view.set(buf);
        return {
            read: arg.length,
            written: buf.length
        };
    };
}

let WASM_VECTOR_LEN = 0;

let wasmModule, wasm;
function __wbg_finalize_init(instance, module) {
    wasm = instance.exports;
    wasmModule = module;
    cachedDataViewMemory0 = null;
    cachedFloat32ArrayMemory0 = null;
    cachedFloat64ArrayMemory0 = null;
    cachedUint8ArrayMemory0 = null;
    wasm.__wbindgen_start();
    return wasm;
}

async function __wbg_load(module, imports) {
    if (typeof Response === 'function' && module instanceof Response) {
        if (typeof WebAssembly.instantiateStreaming === 'function') {
            try {
                return await WebAssembly.instantiateStreaming(module, imports);
            } catch (e) {
                const validResponse = module.ok && expectedResponseType(module.type);

                if (validResponse && module.headers.get('Content-Type') !== 'application/wasm') {
                    console.warn("`WebAssembly.instantiateStreaming` failed because your server does not serve Wasm with `application/wasm` MIME type. Falling back to `WebAssembly.instantiate` which is slower. Original error:\n", e);

                } else { throw e; }
            }
        }

        const bytes = await module.arrayBuffer();
        return await WebAssembly.instantiate(bytes, imports);
    } else {
        const instance = await WebAssembly.instantiate(module, imports);

        if (instance instanceof WebAssembly.Instance) {
            return { instance, module };
        } else {
            return instance;
        }
    }

    function expectedResponseType(type) {
        switch (type) {
            case 'basic': case 'cors': case 'default': return true;
        }
        return false;
    }
}

function initSync(module) {
    if (wasm !== undefined) return wasm;


    if (module !== undefined) {
        if (Object.getPrototypeOf(module) === Object.prototype) {
            ({module} = module)
        } else {
            console.warn('using deprecated parameters for `initSync()`; pass a single object instead')
        }
    }

    const imports = __wbg_get_imports();
    if (!(module instanceof WebAssembly.Module)) {
        module = new WebAssembly.Module(module);
    }
    const instance = new WebAssembly.Instance(module, imports);
    return __wbg_finalize_init(instance, module);
}

async function __wbg_init(module_or_path) {
    if (wasm !== undefined) return wasm;


    if (module_or_path !== undefined) {
        if (Object.getPrototypeOf(module_or_path) === Object.prototype) {
            ({module_or_path} = module_or_path)
        } else {
            console.warn('using deprecated parameters for the initialization function; pass a single object instead')
        }
    }

    if (module_or_path === undefined) {
        module_or_path = new URL('whitemagic_rust_bg.wasm', import.meta.url);
    }
    const imports = __wbg_get_imports();

    if (typeof module_or_path === 'string' || (typeof Request === 'function' && module_or_path instanceof Request) || (typeof URL === 'function' && module_or_path instanceof URL)) {
        module_or_path = fetch(module_or_path);
    }

    const { instance, module } = await __wbg_load(await module_or_path, imports);

    return __wbg_finalize_init(instance, module);
}

export { initSync, __wbg_init as default };
