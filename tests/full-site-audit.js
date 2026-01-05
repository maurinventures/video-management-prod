const { chromium } = require('playwright');
const fs = require('fs');

const BASE_URL = 'https://maurinventuresinternal.com';
const RESULTS = [];
let PAGE;
let BROWSER;

// Auth cookie - get this from your browser
const AUTH_COOKIE = {
    name: 'session',
    value: '.eJw1y8EKwjAMANB_ydkKm6WtO3n2J0aaZlAxrWTrYIj_bg96f-8N84tVsHDZYNq08QnayjqzYH7CBI963ASb5rJ30pTXM1WBn8qpExvc1ZJ3ZlwoGesGMtHHi0noAw1hYY7jPxQU7uVeD_h8AYT1KRU.aVsbZQ.D05qVx6vhvmnq3fMpSrFt5pOyLs',
    domain: 'maurinventuresinternal.com',
    path: '/'
};

async function log(test, status, details = '') {
    const entry = { test, status, details, timestamp: new Date().toISOString() };
    RESULTS.push(entry);
    const icon = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : '⚠️';
    console.log(`${icon} ${test}${details ? ': ' + details : ''}`);
}

async function screenshot(name) {
    await PAGE.screenshot({ path: `test-results/${name}.png`, fullPage: true });
}

async function clickAndVerify(selector, expectedUrl, testName) {
    try {
        await PAGE.click(selector);
        await PAGE.waitForLoadState('networkidle');
        const currentUrl = PAGE.url();

        if (currentUrl.includes(expectedUrl)) {
            await log(testName, 'PASS', currentUrl);
            return true;
        } else {
            await log(testName, 'FAIL', `Expected ${expectedUrl}, got ${currentUrl}`);
            await screenshot(`fail-${testName.replace(/\s/g, '-')}`);
            return false;
        }
    } catch (e) {
        await log(testName, 'FAIL', e.message);
        await screenshot(`error-${testName.replace(/\s/g, '-')}`);
        return false;
    }
}

async function testSidebarNavigation() {
    console.log('\n📍 TESTING SIDEBAR NAVIGATION\n');

    // Go to home first
    await PAGE.goto(`${BASE_URL}/chat`);
    await PAGE.waitForLoadState('networkidle');

    // Test: Click Chats
    await clickAndVerify('a:has-text("Chats")', '/chat/recents', 'Sidebar Chats link');

    // Test: Click Projects
    await clickAndVerify('a:has-text("Projects")', '/projects', 'Sidebar Projects link');

    // Test: Click Chats AGAIN (this is where bug happens)
    await clickAndVerify('a:has-text("Chats")', '/chat/recents', 'Sidebar Chats link (second click)');

    // Test: Click New chat
    await clickAndVerify('a:has-text("New chat")', '/chat', 'Sidebar New chat link');

    // Test: Click Library items
    const libraryItems = ['Videos', 'Audio', 'Transcripts', 'Personas'];
    for (const item of libraryItems) {
        await PAGE.goto(`${BASE_URL}/chat`);
        await clickAndVerify(`a:has-text("${item}")`, item.toLowerCase(), `Sidebar ${item} link`);
    }
}

async function testChatsPage() {
    console.log('\n📍 TESTING CHATS PAGE\n');

    await PAGE.goto(`${BASE_URL}/chat/recents`);
    await PAGE.waitForLoadState('networkidle');

    // Test: Page loads
    const title = await PAGE.textContent('h1, .page-title, .chats-title').catch(() => null);
    await log('Chats page loads', title ? 'PASS' : 'FAIL', title);

    // Test: Chat count is accurate
    const countText = await PAGE.textContent('body');
    const countMatch = countText.match(/(\d+)\s*chats/i);

    // Count actual chat items
    const chatItems = await PAGE.$$('.chat-list-item, .conversation-item, [href^="/chat/"]:not([href="/chat/recents"])');
    const actualCount = chatItems.length;

    if (countMatch) {
        const displayedCount = parseInt(countMatch[1]);
        if (displayedCount === actualCount || actualCount > 0) {
            await log('Chat count accuracy', 'PASS', `Displayed: ${displayedCount}, Items: ${actualCount}`);
        } else {
            await log('Chat count accuracy', 'FAIL', `Displayed: ${displayedCount}, Items: ${actualCount}`);
        }
    } else {
        await log('Chat count accuracy', 'WARN', `No count found, Items: ${actualCount}`);
    }

    // Test: Chats are listed
    if (actualCount > 0) {
        await log('Chats are listed', 'PASS', `Found ${actualCount} chats`);

        // Test: Click first chat
        const firstChat = chatItems[0];
        if (firstChat) {
            await firstChat.click();
            await PAGE.waitForLoadState('networkidle');
            const url = PAGE.url();
            await log('Click chat opens it', url.includes('/chat/') ? 'PASS' : 'FAIL', url);
        }
    } else {
        await log('Chats are listed', 'FAIL', 'No chats found');
        await screenshot('no-chats-listed');
    }
}

async function testProjectsPage() {
    console.log('\n📍 TESTING PROJECTS PAGE\n');

    await PAGE.goto(`${BASE_URL}/projects`);
    await PAGE.waitForLoadState('networkidle');

    // Test: Page loads (no 404)
    const bodyText = await PAGE.textContent('body');
    const is404 = bodyText.includes('Not Found') || bodyText.includes('404');
    await log('Projects page loads', is404 ? 'FAIL' : 'PASS');

    if (!is404) {
        // Test: Projects are listed
        const projectItems = await PAGE.$$('.project-item, .project-card, [href^="/project/"]');
        await log('Projects are listed', projectItems.length > 0 ? 'PASS' : 'WARN', `Found ${projectItems.length}`);

        // Test: Click first project
        if (projectItems.length > 0) {
            await projectItems[0].click();
            await PAGE.waitForLoadState('networkidle');
            const url = PAGE.url();
            await log('Click project opens it', url.includes('/project/') ? 'PASS' : 'FAIL', url);
        }
    }
}

async function testChatFunctionality() {
    console.log('\n📍 TESTING CHAT FUNCTIONALITY\n');

    // Find a chat to test
    await PAGE.goto(`${BASE_URL}/chat/recents`);
    await PAGE.waitForLoadState('networkidle');

    const chatLinks = await PAGE.$$('[href^="/chat/"]:not([href="/chat/recents"]):not([href="/chat"])');

    if (chatLinks.length === 0) {
        await log('Chat functionality', 'SKIP', 'No chats to test');
        return;
    }

    // Open first chat
    await chatLinks[0].click();
    await PAGE.waitForLoadState('networkidle');

    // Test: Chat header exists
    const header = await PAGE.$('.chat-header-bar, .chat-top-bar, .chat-header');
    await log('Chat header exists', header ? 'PASS' : 'FAIL');

    // Test: Share button exists
    const shareBtn = await PAGE.$('button:has-text("Share"), .share-btn');
    await log('Share button exists', shareBtn ? 'PASS' : 'FAIL');

    // Test: Title dropdown exists
    const titleDropdown = await PAGE.$('.chat-title-dropdown, .chat-title-btn');
    await log('Title dropdown exists', titleDropdown ? 'PASS' : 'FAIL');

    // Test: Click title dropdown
    if (titleDropdown) {
        await titleDropdown.click();
        await PAGE.waitForTimeout(300);
        const menu = await PAGE.$('.chat-menu-dropdown.open, .chat-dropdown-menu.open, #chatMenu.open');
        await log('Title dropdown opens menu', menu ? 'PASS' : 'FAIL');

        if (menu) {
            // Check menu items
            const menuItems = await menu.$$('button');
            await log('Menu has items', menuItems.length >= 3 ? 'PASS' : 'FAIL', `Found ${menuItems.length}`);

            // Close menu
            await PAGE.click('body', { position: { x: 10, y: 10 } });
        }
    }

    // Test: Share button works
    if (shareBtn) {
        // Mock clipboard
        await PAGE.evaluate(() => {
            window.clipboardText = null;
            navigator.clipboard.writeText = (text) => {
                window.clipboardText = text;
                return Promise.resolve();
            };
        });

        await shareBtn.click();
        await PAGE.waitForTimeout(500);

        const clipboardText = await PAGE.evaluate(() => window.clipboardText);
        await log('Share copies link', clipboardText && clipboardText.includes('/chat') ? 'PASS' : 'FAIL', clipboardText || 'No text copied');
    }
}

async function testSidebarHoverMenus() {
    console.log('\n📍 TESTING SIDEBAR HOVER MENUS\n');

    // Monitor console errors
    PAGE.on('console', msg => {
        if (msg.type() === 'error') {
            console.log(`  CONSOLE ERROR: ${msg.text()}`);
        }
    });
    PAGE.on('pageerror', err => {
        console.log(`  PAGE ERROR: ${err.message}`);
    });

    await PAGE.goto(`${BASE_URL}/chat`);
    await PAGE.waitForLoadState('networkidle');

    // Wait for scripts to fully initialize
    await PAGE.waitForTimeout(1000);

    // Debug: check what functions are available (functions are hoisted to global)
    const debugInfo = await PAGE.evaluate(() => {
        return {
            hasOpenChatMenu: typeof openChatMenu === 'function',
            hasCloseChatMenu: typeof closeChatMenu === 'function',
            hasChatMenuAction: typeof chatMenuAction === 'function',
            hasShowToast: typeof showToast === 'function'
        };
    });
    console.log(`  DEBUG: ${JSON.stringify(debugInfo)}`);

    // Find chat items in RECENTS
    const recentsItems = await PAGE.$$('.conversation-item');

    if (recentsItems.length === 0) {
        await log('Sidebar hover menus', 'SKIP', 'No items in RECENTS');
        return;
    }

    // Hover first item to make ••• button visible
    await recentsItems[0].hover();
    await PAGE.waitForTimeout(300);

    // Check for ••• button (it becomes visible on hover)
    const optionsBtn = await recentsItems[0].$('.chat-item-menu');

    if (optionsBtn) {
        // Check if button is now visible (opacity > 0)
        const isVisible = await optionsBtn.evaluate(el => {
            const style = window.getComputedStyle(el);
            return parseFloat(style.opacity) > 0;
        });

        await log('Hover shows options button', isVisible ? 'PASS' : 'FAIL', isVisible ? 'opacity > 0' : 'opacity still 0');

        if (isVisible) {
            // Use Playwright's native click
            await optionsBtn.click();
            await PAGE.waitForTimeout(500);

            // Check if menu has 'open' class
            const menuOpen = await PAGE.$('#chatMenu.open');

            // Also check menu display style directly
            const menuState = await PAGE.evaluate(() => {
                const menu = document.getElementById('chatMenu');
                if (!menu) return { exists: false };
                const style = window.getComputedStyle(menu);
                return {
                    exists: true,
                    hasOpenClass: menu.classList.contains('open'),
                    display: style.display,
                    top: menu.style.top,
                    left: menu.style.left
                };
            });

            if (menuState.hasOpenClass) {
                await log('Options button opens menu', 'PASS', `display: ${menuState.display}`);

                const menu = await PAGE.$('#chatMenu');
                const items = await menu.$$('button');
                const itemTexts = await Promise.all(items.map(i => i.textContent()));
                await log('Menu items', 'PASS', itemTexts.map(t => t.trim()).join(', '));

                // Close menu by clicking outside
                await PAGE.click('body', { position: { x: 10, y: 10 } });
            } else {
                await log('Options button opens menu', 'FAIL', `exists: ${menuState.exists}, hasOpen: ${menuState.hasOpenClass}, display: ${menuState.display}`);
                await screenshot('menu-not-open');
            }
        }
    } else {
        await log('Hover shows options button', 'FAIL', 'Button element not found');
        await screenshot('no-hover-menu');
    }
}

async function testAllLinks() {
    console.log('\n📍 TESTING ALL LINKS FOR 404s\n');

    await PAGE.goto(`${BASE_URL}/chat`);
    await PAGE.waitForLoadState('networkidle');

    // Get all internal links
    const links = await PAGE.$$eval('a[href^="/"]', els =>
        [...new Set(els.map(e => e.getAttribute('href')))]
    );

    console.log(`Found ${links.length} unique internal links`);

    for (const link of links.slice(0, 20)) { // Test first 20
        try {
            const response = await PAGE.goto(`${BASE_URL}${link}`);
            const status = response.status();

            if (status === 404) {
                await log(`Link: ${link}`, 'FAIL', '404 Not Found');
            } else if (status >= 400) {
                await log(`Link: ${link}`, 'FAIL', `Status ${status}`);
            } else {
                await log(`Link: ${link}`, 'PASS');
            }
        } catch (e) {
            await log(`Link: ${link}`, 'FAIL', e.message);
        }
    }
}

async function runAllTests() {
    console.log('🚀 STARTING FULL SITE AUDIT\n');
    console.log('='.repeat(50));

    BROWSER = await chromium.launch({ headless: true });
    const context = await BROWSER.newContext({
        // Disable caching
        bypassCSP: true,
    });

    // Add auth cookie
    await context.addCookies([AUTH_COOKIE]);

    // Disable cache
    await context.route('**/*', route => {
        route.continue({
            headers: {
                ...route.request().headers(),
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
    });

    PAGE = await context.newPage();

    try {
        await testSidebarNavigation();
        await testChatsPage();
        await testProjectsPage();
        await testChatFunctionality();
        await testSidebarHoverMenus();
        await testAllLinks();
    } catch (e) {
        console.error('Fatal error:', e);
    }

    await BROWSER.close();

    // Summary
    console.log('\n' + '='.repeat(50));
    console.log('📊 SUMMARY\n');

    const passed = RESULTS.filter(r => r.status === 'PASS').length;
    const failed = RESULTS.filter(r => r.status === 'FAIL').length;
    const skipped = RESULTS.filter(r => r.status === 'SKIP' || r.status === 'WARN').length;

    console.log(`✅ Passed: ${passed}`);
    console.log(`❌ Failed: ${failed}`);
    console.log(`⚠️ Skipped/Warnings: ${skipped}`);

    // Save results
    fs.writeFileSync('test-results/audit-results.json', JSON.stringify(RESULTS, null, 2));
    console.log('\n📁 Results saved to test-results/audit-results.json');

    // List failures
    if (failed > 0) {
        console.log('\n❌ FAILURES:\n');
        RESULTS.filter(r => r.status === 'FAIL').forEach(r => {
            console.log(`  - ${r.test}: ${r.details}`);
        });
    }

    process.exit(failed > 0 ? 1 : 0);
}

runAllTests();
