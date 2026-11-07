# EXPLORATORY — the most common function fingerprints (exact signal-presence signatures), population DB v2.12.0-b64f42bf

- functions (loc ≥ 3): 6,936,799; distinct signatures 314,979; top 6 cover 10.0%

## #1: {struct_linear, struct_args, struct_func_start}

- **177,180 functions (2.6%)** in **386 repos**; largest single repo holds 9%
- size: median 3 lines (IQR 3–5)
- in test paths: 35%
- languages: javascript 28%, cpp 17%, typescript 17%, kotlin 8%, swift 5%, ruby 4%, dart 4%, rust 4%
- archetypes: Parameter Forwarders 57%, Interface Declarations 40%, I/O & Config Routines 2%, Many-Argument Workhorses 1%, State Mutators 0%
- most common names: `foo` 4,811, `main` 3,780, `f#` 2,068, `f` 2,010, `constructor` 1,503, `foo#` 1,398, `bar` 1,197, `page` 1,092, `get` 990, `__init__` 989, `init` 877, `render` 843

Examples:

- rust · swc · `visit_export_all` (4 lines)

```
    fn visit_export_all(&mut self, n: &ExportAll) {
        let src = str_to_atom(&n.src);
        *self.flag_record.entry(src).or_default() |= LinkFlag::EXPORT_STAR;
    }

    fn visit_import(&mut self, _: &Import) {
        self.dynamic_import_found = true;
```

- cpp · runtime · `LCM` (4 lines)

```
DWORD LCM(DWORD u, DWORD v)
{
    return u / GCD(u, v) * v;
}
#endif

bool InitLargePagesPrivilege()
```

- typescript · workers-sdk · `_hasInnerBindings` (3 lines)

```
	_hasInnerBindings(): boolean {
		return !$.utils.isNull($.utils.getPointer(2, this));
	}
	_initInnerBindings(length: number): $.List<Worker_Binding> {
		return $.utils.initList(
			2,
			Worker_Binding_WrappedBinding._InnerBindings,
```

- javascript · discourse · `staffFlagsAvailable` (3 lines)

```
  get staffFlagsAvailable() {
    return this.flagsAvailable.length > 1;
  }

  get submitEnabled() {
    if (!this.selected) {
      return false;
```

- dart · sdk · `test` (4 lines)

```
  void test() {
    var x = deconstruct(this);
    x.foo; // Check that we implement A<dynamic>
  }
}

// Test the same examples with top level normalization
```

- typescript · material-ui · `createObjectType` (6 lines)

```
export function createObjectType(init: { jsDoc: string | undefined }): ObjectType {
  return {
    type: 'ObjectNode',
    jsDoc: init.jsDoc,
  };
}

export function createStringType(init: { jsDoc: string | undefined }): StringType {
```

## #2: {struct_linear, struct_args, struct_func_start, arch_api}

- **170,862 functions (2.5%)** in **318 repos**; largest single repo holds 10%
- size: median 4 lines (IQR 3–5)
- in test paths: 23%
- languages: php 22%, python 19%, java 17%, c 15%, csharp 10%, typescript 7%, zig 3%, go 2%
- archetypes: Parameter Forwarders 50%, Interface Declarations 47%, I/O & Config Routines 2%, Many-Argument Workhorses 1%, Compute Cores 0%
- most common names: `main` 1,379, `tostring` 1,127, `getname` 870, `getclassname` 756, `__construct` 682, `getvalue` 629, `init` 615, `foo` 545, `gethashcode` 533, `parsefrom` 526, `equals` 517, `create` 453

Examples:

- java · spring-boot · `getWeb` (3 lines)

```
	public Web getWeb() {
		return this.web;
	}

	public System getSystem() {
		return this.system;
	}
```

- php · magento2 · `addFormCodeFilter` (4 lines)

```
    public function addFormCodeFilter($code)
    {
        return $this->addFieldToFilter('main_table.form_code', $code);
    }

    /**
     * Set order by attribute sort order
```

- python · freebsd-src · `testDefaultBehaviorWithShards` (8 lines)

```
  def testDefaultBehaviorWithShards(self):
    """Tests the behavior without the filter, with sharding enabled."""

    self.RunAndVerifyWithSharding(None, 1, ACTIVE_TESTS)
    self.RunAndVerifyWithSharding(None, 2, ACTIVE_TESTS)
    self.RunAndVerifyWithSharding(None, len(ACTIVE_TESTS) - 1, ACTIVE_TESTS)
    self.RunAndVerifyWithSharding(None, len(ACTIVE_TESTS), ACTIVE_TESTS)
    self.RunAndVerifyWithSharding(None, len(ACTIVE_TESTS) + 1, ACTIVE_TESTS)
```

- csharp · runtime · `ReadAttributeValue` (4 lines)

```
        public override bool ReadAttributeValue()
        {
            return _reader.ReadAttributeValue();
        }

        //
        // IDisposable interface
```

- java · selenium · `fromElement` (3 lines)

```
    public static Origin fromElement(WebElement element) {
      return new Origin(Require.nonNull("Element", element));
    }
  }

  public static PointerEventProperties eventProperties() {
    return new PointerEventProperties();
```

- csharp · runtime · `ModuloNullableShort` (4 lines)

```
        public static short ModuloNullableShort(short a, short b)
        {
            return (short)(a % b);
        }

        public static uint ModuloNullableUInt(uint a, uint b)
        {
```

## #3: {struct_branch, struct_linear, struct_args, struct_func_start, struct_class_start, state_flux, state_pointers, def_encapsulation}

- **98,954 functions (1.4%)** in **40 repos**; largest single repo holds 77%
- size: median 23 lines (IQR 17–35)
- in test paths: 1%
- languages: c 100%, go 0%, cpp 0%
- archetypes: C Struct Operations 91%, Many-Argument Workhorses 6%, Compute Cores 3%, I/O & Config Routines 0%, Stateful Encapsulated Methods 0%
- most common names: `__acquires` 64, `__must_hold` 56, `max#_probe` 48, `sd_init_controls` 30, `ad#_probe` 29, `rt#_probe` 27, `__releases` 26, `ov#_enum_mbus_code` 26, `wm#_i#c_probe` 26, `max#_i#c_probe` 20, `lm#_probe` 19, `vidioc_g_frequency` 19

Examples:

- c · freebsd-src · `vtblk_queue_complete_one` (28 lines)

```
static struct bio *
vtblk_queue_complete_one(struct vtblk_softc *sc, struct vtblk_request *req)
{
	struct bio *bp;

	if (sc->vtblk_req_ordered != NULL) {
		MPASS(sc->vtblk_req_ordered == req);
		sc->vtblk_req_ordered = NULL;
```

## #4: {struct_linear, struct_args, struct_func_start, state_pointers, def_encapsulation}

- **87,078 functions (1.3%)** in **89 repos**; largest single repo holds 57%
- size: median 5 lines (IQR 4–6)
- in test paths: 3%
- languages: c 96%, go 3%, csharp 0%, solidity 0%, swift 0%, livecode 0%, python 0%, assembly 0%
- archetypes: Encapsulated Accessors 93%, Stateful Encapsulated Methods 4%, Parameter Forwarders 2%, Interface Declarations 0%, I/O & Config Routines 0%
- most common names: `addknowntypes` 181, `test_#` 127, `__releases` 127, `__acquires` 72, `impl_from_iunknown` 47, `init_nls_cp#` 46, `exit_nls_cp#` 46, `impl_from_iclassfactory` 43, `releasehandle` 42, `to_state` 37, `foo#` 36, `vec_all_eq` 30

Examples:

- c · linux · `mega_create_proc_entry` (3 lines)

```
static inline void mega_create_proc_entry(int index, struct proc_dir_entry *parent)
{
}
#endif


/*
```

- go · go · `newImplNoInline` (3 lines)

```
func newImplNoInline() *Impl {
	return &Impl{} // ERROR "&Impl{} escapes to heap$"
}

//go:noinline
func newImpl2ret2() (string, *Impl2) {
	return "str", &Impl2{} // ERROR "&Impl2{} escapes to heap$"
```

- solidity · openzeppelin-contracts · `_safeTransfer` (4 lines)

```
    function _safeTransfer(address from, address to, uint256 tokenId, bytes memory data) internal virtual {
        _transfer(from, to, tokenId);
        ERC721Utils.checkOnERC721Received(_msgSender(), from, to, tokenId, data);
    }

    /**
     * @dev Approve `to` to operate on `tokenId`
```

- csharp · runtime · `test_282` (7 lines)

```
    private static unsafe long test_282(B[,] ab, long i, long j)
    {
        fixed (B* pb = &ab[i, j])
        {
            return AA.get_i2(pb->m_bval);
        }
    }
    private static unsafe long test_289(B* pb1)
```

- c · linux · `btrfs_inc_block_group_reservations` (5 lines)

```
static void
btrfs_inc_block_group_reservations(struct btrfs_block_group *bg)
{
	atomic_inc(&bg->reservations);
}

/*
```

- c · linux · `cdns_clk_rst_deinit` (5 lines)

```
static void cdns_clk_rst_deinit(struct cdns_starfive *data)
{
	reset_control_assert(data->resets);
	clk_bulk_disable_unprepare(data->num_clks, data->clks);
}

static int cdns_starfive_probe(struct platform_device *pdev)
```

## #5: {struct_linear, struct_args, struct_func_start, arch_api, state_flux}

- **84,383 functions (1.2%)** in **294 repos**; largest single repo holds 14%
- size: median 5 lines (IQR 4–9)
- in test paths: 35%
- languages: python 39%, php 27%, csharp 11%, java 10%, c 4%, typescript 2%, swift 2%, rust 1%
- archetypes: Parameter Forwarders 70%, Interface Declarations 21%, I/O & Config Routines 5%, Many-Argument Workhorses 3%, Compute Cores 0%
- most common names: `__construct` 7,823, `foo#` 6,215, `setup` 1,724, `init` 974, `setupclass` 926, `execute` 416, `clear` 329, `setup_method` 329, `run` 291, `create` 274, `reset` 262, `add` 245

Examples:

- csharp · runtime · `foo2233` (5 lines)

```
        public static void foo2233()
        {
            ActualResult = (ActualResult + "2233");
            return;
        }

        public static void foo2234()
```

- python · django · `get_search_fields` (4 lines)

```
    def get_search_fields(self, request):
        search_fields = super().get_search_fields(request)
        search_fields += ("age",)
        return search_fields


class EmptyValueChildAdmin(admin.ModelAdmin):
```

- php · magento2 · `__construct` (5 lines)

```
    public function __construct(
        ModuleDataSetupInterface $moduleDataSetup
    ) {
        $this->moduleDataSetup = $moduleDataSetup;
    }

    /**
```

- java · elasticsearch · `LengthFunctionProcessor` (3 lines)

```
    public LengthFunctionProcessor(StreamInput in) throws IOException {
        input = in.readNamedWriteable(Processor.class);
    }

    @Override
    public final void writeTo(StreamOutput out) throws IOException {
        out.writeNamedWriteable(input);
```

- c · illumos-gate · `set_using_pkcs_functions` (4 lines)

```
void set_using_pkcs_functions( int val )
{
    using_pkcs_functions = val;
}


/*
```

- python · scipy · `setup` (4 lines)

```
    def setup(self, n, m):
        rng = np.random.default_rng(1234)
        self.A = sparse.eye(n, n) + sparse.rand(n, n, density=0.01, random_state=rng)
        self.b = np.ones(n)

    def time_inner(self, n, m):
        lgmres(self.A, self.b, inner_m=m, maxiter=1)
```

## #6: {struct_branch, struct_linear, struct_args, struct_func_start, state_flux, state_pointers, def_encapsulation}

- **73,614 functions (1.1%)** in **84 repos**; largest single repo holds 39%
- size: median 19 lines (IQR 13–29)
- in test paths: 2%
- languages: c 98%, go 2%, csharp 0%, livecode 0%, solidity 0%, python 0%, swift 0%, dart 0%
- archetypes: Stateful Encapsulated Methods 79%, Many-Argument Workhorses 8%, Encapsulated Accessors 7%, Compute Cores 3%, I/O & Config Routines 2%
- most common names: `putimage#` 39, `vertline#` 29, `diagline#` 28, `cleararea#` 28, `horzline#` 28, `i_psvc_constructor_#_#` 23, `__must_hold` 20, `classfactory_queryinterface` 16, `flush_events` 16, `init_hw` 14, `releasehandle` 13, `prog_name` 13

Examples:

- c · reactos · `IDirectPlay4Impl_AddRef` (12 lines)

```
static ULONG WINAPI IDirectPlay4Impl_AddRef(IDirectPlay4 *iface)
{
    IDirectPlayImpl *This = impl_from_IDirectPlay4( iface );
    ULONG ref = InterlockedIncrement( &This->ref4 );

    TRACE( "(%p) ref4=%d\n", This, ref );

    if ( ref == 1 )
```

- go · go · `walkRecv` (10 lines)

```
func walkRecv(n *ir.UnaryExpr) ir.Node {
	if n.Typecheck() == 0 {
		base.Fatalf("missing typecheck: %+v", n)
	}
	init := ir.TakeInit(n)

	n.X = walkExpr(n.X, &init)
	call := walkExpr(mkcall1(chanfn("chanrecv1", 2, n.X.Type()), nil, &init, n.X, typecheck.NodNil()), &init)
```

- livecode · livecode · `_svgParsePreserveAspectRatio` (14 lines)

```
private function _svgParsePreserveAspectRatio @xValue
	if xValue is "none" then
		return true
	end if
	if word 1 of xValue is among the items of "xMinYMin,xMidYMin,xMaxYMin,xMinYMid,xMidYMid,xMaxYMid,xMinYMax,xMidYMax,xMaxYMax" then
		if word 2 of xValue is empty then
			put " meet" after xValue
		end if
```

- csharp · PowerToys · `TryLoadIndirectString` (13 lines)

```
    private static bool TryLoadIndirectString(string input, out string? output)
    {
        var outBuffer = new StringBuilder(1024);
        var hr = NativeMethods.SHLoadIndirectString(input, outBuffer, outBuffer.Capacity, IntPtr.Zero);
        if (hr == 0)
        {
            output = outBuffer.ToString();
            return !string.IsNullOrWhiteSpace(output);
```

- c · reactos · `IRecordInfoImpl_GetFieldNames` (22 lines)

```
static HRESULT WINAPI IRecordInfoImpl_GetFieldNames(IRecordInfo *iface, ULONG *pcNames,
                                                BSTR *rgBstrNames)
{
    IRecordInfoImpl *This = impl_from_IRecordInfo(iface);
    ULONG n = This->n_vars, i;

    TRACE("(%p)->(%p %p)\n", This, pcNames, rgBstrNames);

```

- c · ldb-ecm-raspberry-pi · `HorzLine24` (8 lines)

```
static void HorzLine24 (INTDC* dc, uint_fast32_t cx, int_fast8_t dir) {
	RGB* __attribute__((aligned(1))) video_wr_ptr = (RGB*)(uintptr_t)(dc->fb + (dc->curPos.y * dc->pitch * 3) + (dc->curPos.x * 3));
	for (uint_fast32_t i = 0; i < cx; i++) {						// For each x pixel
		video_wr_ptr[0] = dc->TxtColor.rgb;							// Write the colour
		video_wr_ptr += dir;										// Positive offset to next pixel
	}
	dc->curPos.x += (cx * dir);										// Set current x position
}
```

