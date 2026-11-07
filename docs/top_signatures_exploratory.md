# EXPLORATORY — the most common function fingerprints (exact signal-presence signatures), population DB v2.12.0-b64f42bf

- functions (loc ≥ 3): 6,936,799; distinct signatures 314,979; top 5 cover 8.9%

## #1: {struct_linear, struct_args, struct_func_start}

- **177,180 functions (2.6%)** in **386 repos**; largest single repo holds 9%
- size: median 3 lines (IQR 3–5)
- in test paths: 35%
- languages: javascript 28%, cpp 17%, typescript 17%, kotlin 8%, swift 5%, ruby 4%, dart 4%, rust 4%
- archetypes: Parameter Forwarders 57%, Interface Declarations 40%, I/O & Config Routines 2%, Many-Argument Workhorses 1%, State Mutators 0%
- most common names: `foo` 4,811, `main` 3,780, `f#` 2,068, `f` 2,010, `constructor` 1,503, `foo#` 1,398, `bar` 1,197, `page` 1,092, `get` 990, `__init__` 989, `init` 877, `render` 843

Examples:

- typescript · Excalibur · `easeInQuint` (3 lines)

```
export function easeInQuint(currentTime: number): number {
  return currentTime * currentTime * currentTime * currentTime * currentTime;
}

// Decelerating to zero velocity
export function easeOutQuint(currentTime: number): number {
  const t1 = currentTime - 1;
```

- go · go · `infoPlist` (19 lines)

```
func infoPlist(pkgpath string) string {
	return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
<key>CFBundleName</key><string>golang.gotest</string>
<key>CFBundleSupportedPlatforms</key><array><string>iPhoneOS</string></array>
<key>CFBundleExecutable</key><string>gotest</string>
```

- cpp · runtime · `TriggerCustomMarshaler` (7 lines)

```
    virtual HRESULT STDMETHODCALLTYPE TriggerCustomMarshaler(
        /*[in]*/ IUnknown* objIn,
        /*[in,out]*/ IUnknown** objRef,
        /*[out,retval]*/ IUnknown* pRetVal)
    {
        return E_NOTIMPL;
    }
    virtual HRESULT STDMETHODCALLTYPE DoubleHVAValues (
```

- javascript · swc · `formatUTCWeekNumberSunday` (3 lines)

```
function formatUTCWeekNumberSunday(d, p) {
    return pad(utcSunday.count(utcYear(d) - 1, d), p, 2);
}
function UTCdISO(d) {
    var day = d.getUTCDay();
    return day >= 4 || 0 === day ? utcThursday(d) : utcThursday.ceil(d);
}
```

- cpp · zig · `IsWindowsXPSP2OrGreater` (3 lines)

```
VERSIONHELPERAPI IsWindowsXPSP2OrGreater(void) {
    return IsWindowsVersionOrGreater(HIBYTE(_WIN32_WINNT_WINXP), LOBYTE(_WIN32_WINNT_WINXP), 2);
}

VERSIONHELPERAPI IsWindowsXPSP3OrGreater(void) {
    return IsWindowsVersionOrGreater(HIBYTE(_WIN32_WINNT_WINXP), LOBYTE(_WIN32_WINNT_WINXP), 3);
}
```

- kotlin · kotlin · `serializeSingleTarget` (11 lines)

```
    fun serializeSingleTarget(
        node: CirRootNode,
        targetIndex: Int,
        statsCollector: StatsCollector?,
        moduleConsumer: (KlibModuleMetadata) -> Unit
    ) {
        node.accept(
            CirTreeSerializationVisitor(statsCollector, moduleConsumer),
```

## #2: {struct_linear, struct_args, struct_func_start, arch_api}

- **170,862 functions (2.5%)** in **318 repos**; largest single repo holds 10%
- size: median 4 lines (IQR 3–5)
- in test paths: 23%
- languages: php 22%, python 19%, java 17%, c 15%, csharp 10%, typescript 7%, zig 3%, go 2%
- archetypes: Parameter Forwarders 50%, Interface Declarations 47%, I/O & Config Routines 2%, Many-Argument Workhorses 1%, Compute Cores 0%
- most common names: `main` 1,379, `tostring` 1,127, `getname` 870, `getclassname` 756, `__construct` 682, `getvalue` 629, `init` 615, `foo` 545, `gethashcode` 533, `parsefrom` 526, `equals` 517, `create` 453

Examples:

- php · mediawiki · `provideAddDeletedUserFilter` (30 lines)

```
	public static function provideAddDeletedUserFilter() {
		return [
			'unauthorized' => [
				false,
				[
					'tables' => [ 'table' ],
					'fields' => [ 'hu_deleted' => '1=0' ],
					'conds' => [ '(SELECT  1  FROM "block_target" "hu_block_target" ' .
```

- python · cpython · `remove_writer` (4 lines)

```
    def remove_writer(self, fd):
        """Remove a writer callback."""
        self._ensure_fd_no_transport(fd)
        return self._remove_writer(fd)

    async def sock_recv(self, sock, n):
        """Receive data from the socket.
```

- c · sokol-zig · `sokol_main` (6 lines)

```
sapp_desc sokol_main(int argc, char* argv[]) {
    _SOKOL_UNUSED(argc);
    _SOKOL_UNUSED(argv);
    _SAPP_STRUCT(sapp_desc, desc);
    return desc;
}
#else
/* likewise, in normal mode, sapp_run() is just an empty stub */
```

- typescript · vscode · `addOverlayWidget` (5 lines)

```
	public addOverlayWidget(widgetData: IOverlayWidgetData): void {
		this._overlayWidgets.addWidget(widgetData.widget);
		this.layoutOverlayWidget(widgetData);
		this._scheduleRender();
	}

	public layoutOverlayWidget(widgetData: IOverlayWidgetData): void {
```

- python · cpython · `do_work` (20 lines)

```
            def do_work():
                _interpreters.run_string(interpid, f"""if True:
                    waiting = False
                    done = False
                    def subthread():
                        while not waiting:
                            pass
                        os.write({w_ready}, b'\\0')
```

- dart · sdk · `test` (3 lines)

```
int test(int a) {
  return a;
}

main() {
  // 1 positional arg, as expected. Param x does not exist.
  test(10, x: 99);
```

## #3: {struct_branch, struct_linear, struct_args, struct_func_start, struct_class_start, state_flux, state_pointers, def_encapsulation}

- **98,954 functions (1.4%)** in **40 repos**; largest single repo holds 77%
- size: median 23 lines (IQR 17–35)
- in test paths: 1%
- languages: c 100%, go 0%, cpp 0%
- archetypes: C Struct Operations 91%, Many-Argument Workhorses 6%, Compute Cores 3%, I/O & Config Routines 0%, Stateful Encapsulated Methods 0%
- most common names: `__acquires` 64, `__must_hold` 56, `max#_probe` 48, `sd_init_controls` 30, `ad#_probe` 29, `rt#_probe` 27, `__releases` 26, `ov#_enum_mbus_code` 26, `wm#_i#c_probe` 26, `max#_i#c_probe` 20, `lm#_probe` 19, `vidioc_g_frequency` 19

Examples:

- c · linux · `__flush_addrs` (11 lines)

```
static void __flush_addrs(struct list_head *list)
{
	while (!list_empty(list)) {
		struct mptcp_pm_addr_entry *cur;

		cur = list_entry(list->next,
				 struct mptcp_pm_addr_entry, list);
		list_del_rcu(&cur->list);
```

## #4: {struct_linear, struct_args, struct_func_start, state_pointers, def_encapsulation}

- **87,078 functions (1.3%)** in **89 repos**; largest single repo holds 57%
- size: median 5 lines (IQR 4–6)
- in test paths: 3%
- languages: c 96%, go 3%, csharp 0%, solidity 0%, swift 0%, livecode 0%, python 0%, assembly 0%
- archetypes: Encapsulated Accessors 93%, Stateful Encapsulated Methods 4%, Parameter Forwarders 2%, Interface Declarations 0%, I/O & Config Routines 0%
- most common names: `addknowntypes` 181, `test_#` 127, `__releases` 127, `__acquires` 72, `impl_from_iunknown` 47, `init_nls_cp#` 46, `exit_nls_cp#` 46, `impl_from_iclassfactory` 43, `releasehandle` 42, `to_state` 37, `foo#` 36, `vec_all_eq` 30

Examples:

- c · linux · `wle` (4 lines)

```
static inline void wle(uint32_t val, uint32_t *x)
{
	put_unaligned_le32(val, x);
}

static inline void w8be(uint64_t val, uint64_t *x)
{
```

- go · grafana · `schema_pkg_apis_iam_v0alpha1_GetSearchTeamsResponse` (69 lines)

```
func schema_pkg_apis_iam_v0alpha1_GetSearchTeamsResponse(ref common.ReferenceCallback) common.OpenAPIDefinition {
	return common.OpenAPIDefinition{
		Schema: spec.Schema{
			SchemaProps: spec.SchemaProps{
				Type: []string{"object"},
				Properties: map[string]spec.Schema{
					"kind": {
						SchemaProps: spec.SchemaProps{
```

- solidity · openzeppelin-contracts · `decodeBool` (3 lines)

```
    function decodeBool(bytes memory item) internal pure returns (bool) {
        return readBool(item.asSlice());
    }

    /// @dev Decode an RLP encoded address from bytes. See {readAddress}
    function decodeAddress(bytes memory item) internal pure returns (address) {
        return readAddress(item.asSlice());
```

- csharp · runtime · `test_51` (7 lines)

```
    private static unsafe long test_51()
    {
        fixed (B* pb = &AA.s_x.m_b)
        {
            return pb[0].m_bval;
        }
    }
    private static unsafe long test_58(B* pb, long i)
```

- c · linux · `thread_wake_up` (4 lines)

```
static void thread_wake_up(struct timer_list *unused)
{
	wake_up_interruptible_all(&speakup_event);
}

static DEFINE_TIMER(thread_timer, thread_wake_up);

```

- c · freebsd-src · `test_serialize_tags` (11 lines)

```
static void test_serialize_tags(void **_CBOR_UNUSED(_state)) {
  cbor_item_t *item = cbor_new_tag(21);
  cbor_item_t *one = cbor_build_uint8(1);
  cbor_tag_set_item(item, one);

  assert_size_equal(2, cbor_serialize(item, buffer, 512));
  assert_memory_equal(buffer, ((unsigned char[]){0xD5, 0x01}), 2);
  assert_size_equal(cbor_serialized_size(item), 2);
```

## #5: {struct_linear, struct_args, struct_func_start, arch_api, state_flux}

- **84,383 functions (1.2%)** in **294 repos**; largest single repo holds 14%
- size: median 5 lines (IQR 4–9)
- in test paths: 35%
- languages: python 39%, php 27%, csharp 11%, java 10%, c 4%, typescript 2%, swift 2%, rust 1%
- archetypes: Parameter Forwarders 70%, Interface Declarations 21%, I/O & Config Routines 5%, Many-Argument Workhorses 3%, Compute Cores 0%
- most common names: `__construct` 7,823, `foo#` 6,215, `setup` 1,724, `init` 974, `setupclass` 926, `execute` 416, `clear` 329, `setup_method` 329, `run` 291, `create` 274, `reset` 262, `add` 245

Examples:

- php · symfony · `setResolvedTypeFactory` (6 lines)

```
    public function setResolvedTypeFactory(ResolvedFormTypeFactoryInterface $resolvedTypeFactory): static
    {
        $this->resolvedTypeFactory = $resolvedTypeFactory;

        return $this;
    }

    public function addExtension(FormExtensionInterface $extension): static
```

- java · gradle · `setDeployName` (3 lines)

```
    public void setDeployName(String deployName) {
        this.deployName = deployName;
    }

    public String getContextPath() {
        return contextPath;
    }
```

- python · tensorflow · `testWithPrivateSpecialType` (9 lines)

```
  def testWithPrivateSpecialType(self):
    rt = ragged_tensor.RaggedTensor.from_value_rowids(
        array_ops.constant([[1, 2], [3, 4], [5, 6]]), [0, 0, 1])
    pst = _PrivateSpecialType(rt)
    pst_shape = array_ops.shape_v2(pst)
    st = structured_tensor.StructuredTensor.from_fields_and_rank({"r": pst}, 1)
    st_shape = st._ragged_shape
    self.assertEqual(1, st.rank)
```

- c · reactos · `NtUserSetImeHotKey` (15 lines)

```
BOOL
NTAPI
NtUserSetImeHotKey(
    _In_ DWORD dwHotKeyId,
    _In_ UINT uModifiers,
    _In_ UINT uVirtualKey,
    _In_opt_ HKL hKL,
    _In_ DWORD dwAction)
```

- php · symfony · `getMessageCount` (8 lines)

```
    public function getMessageCount(): int
    {
        $queryBuilder = $this->createAvailableMessagesQueryBuilder()
            ->select('COUNT(m.id) AS message_count')
            ->setMaxResults(1);

        return $this->executeQuery($queryBuilder->getSQL(), $queryBuilder->getParameters(), $queryBuilder->getParameterTypes())->fetchOne();
    }
```

- lua · darwin-xnu · `QueueTest` (6 lines)

```
function QueueTest(num_cores)
    table.insert(tests, {
        path = benchmark.opt.path,
        num_cores = num_cores,
    })
end

if benchmark.opt.through_max_workers then
```

