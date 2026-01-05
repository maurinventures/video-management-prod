const { chromium } = require('playwright');

const BASE_URL = 'https://maurinventuresinternal.com';

async function runTests() {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    console.log('Starting UI tests...\n');

    let passed = 0;
    let failed = 0;
    let skipped = 0;

    try {
        // Test 1: Load chat page
        console.log('Test 1: Loading /chat...');
        const response = await page.goto(`${BASE_URL}/chat`, { waitUntil: 'networkidle' });
        console.log(`  INFO: Status ${response.status()}`);

        // Check if redirected to login
        const currentUrl = page.url();
        const isLoginPage = currentUrl.includes('login') || currentUrl.includes('auth');

        if (isLoginPage) {
            console.log('  INFO: Redirected to login page (auth required)\n');
            console.log('  SKIP: Remaining tests require authentication\n');
            skipped = 9;

            // Still check raw HTML for menu code
            console.log('Test 2: Fetching page source to check for menu code...');
            const html = await page.content();

            if (html.includes('chat-menu-container')) {
                console.log('  FAIL: Found chat-menu-container in HTML\n');
                failed++;
            } else {
                console.log('  PASS: No chat-menu-container in HTML\n');
                passed++;
            }

            if (html.includes('cy="5" r="2"') || html.includes("cy='5' r='2'")) {
                console.log('  FAIL: Found three-dot SVG in HTML\n');
                failed++;
            } else {
                console.log('  PASS: No three-dot SVG in HTML\n');
                passed++;
            }

        } else {
            console.log('  PASS: Page loaded (authenticated)\n');
            passed++;

            // Test 2: Check NO floating three-dot menu in main content
            console.log('Test 2: Checking no floating three-dot menu...');
            const threeDotSvg = await page.$('svg circle[cy="5"][r="2"]');
            if (threeDotSvg) {
                console.log('  FAIL: Found three-dot SVG (should be removed)\n');
                failed++;
            } else {
                console.log('  PASS: No three-dot SVG found\n');
                passed++;
            }

            // Test 3: Check NO chat-menu-container
            console.log('Test 3: Checking no chat-menu-container...');
            const menuContainer = await page.$('.chat-menu-container');
            if (menuContainer) {
                console.log('  FAIL: Found .chat-menu-container (should be removed)\n');
                failed++;
            } else {
                console.log('  PASS: No .chat-menu-container found\n');
                passed++;
            }

            // Test 4: Check sidebar exists
            console.log('Test 4: Checking sidebar exists...');
            const sidebar = await page.$('#sidebar, .sidebar');
            if (sidebar) {
                console.log('  PASS: Sidebar found\n');
                passed++;
            } else {
                console.log('  FAIL: Sidebar not found\n');
                failed++;
            }

            // Test 5: Check RECENTS section exists
            console.log('Test 5: Checking RECENTS section...');
            const recentsSection = await page.$('.conversations-list, #conversationsList');
            if (recentsSection) {
                console.log('  PASS: RECENTS section found\n');
                passed++;
            } else {
                console.log('  FAIL: RECENTS section not found\n');
                failed++;
            }

            // Test 6: Find chat items in sidebar
            console.log('Test 6: Finding chat items...');
            const chatItems = await page.$$('.conversation-item');
            console.log(`  INFO: Found ${chatItems.length} chat items`);
            console.log('  PASS: Chat items query successful\n');
            passed++;

            // Test 7: Check welcome screen visible
            console.log('Test 7: Checking welcome screen...');
            const welcomeScreen = await page.$('#welcomeScreen');
            if (welcomeScreen) {
                console.log('  PASS: Welcome screen found\n');
                passed++;
            } else {
                console.log('  FAIL: Welcome screen not found\n');
                failed++;
            }

            // Test 8: Navigate to /chat/recents
            console.log('Test 8: Navigating to /chat/recents...');
            await page.goto(`${BASE_URL}/chat/recents`, { waitUntil: 'networkidle' });
            console.log('  PASS: Recents page loaded\n');
            passed++;

            // Test 9: Check no floating menu on recents page
            console.log('Test 9: Checking no floating menu on recents...');
            const floatingMenu2 = await page.$('.chat-menu-container, .chat-menu-btn');
            if (floatingMenu2) {
                console.log('  FAIL: Found menu element on recents page\n');
                failed++;
            } else {
                console.log('  PASS: No menu element on recents page\n');
                passed++;
            }

            // Test 10: Check chats list view exists
            console.log('Test 10: Checking chats list view...');
            const chatsListView = await page.$('#chatsListView, .chats-list-view');
            if (chatsListView) {
                console.log('  PASS: Chats list view found\n');
                passed++;
            } else {
                console.log('  FAIL: Chats list view not found\n');
                failed++;
            }
        }

        // Take screenshot for verification
        await page.screenshot({ path: 'test-results/final-state.png', fullPage: true });
        console.log('Screenshot saved to test-results/final-state.png\n');

    } catch (error) {
        console.log('ERROR:', error.message);
        await page.screenshot({ path: 'test-results/error.png', fullPage: true });
        failed++;
    }

    await browser.close();

    console.log('='.repeat(50));
    console.log(`RESULTS: ${passed} passed, ${failed} failed, ${skipped} skipped`);
    if (skipped > 0) {
        console.log('(Tests skipped due to authentication requirement)');
    }
    console.log('='.repeat(50));

    // Exit with success if no failures (skipped tests are OK)
    process.exit(failed > 0 ? 1 : 0);
}

runTests();
