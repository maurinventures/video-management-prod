#!/usr/bin/env node

/**
 * MV Internal - Interactive Element Verification Script
 *
 * This script validates that all interactive elements discovered in the
 * Full Interactive Element Audit are properly defined and accessible.
 *
 * Run: node tests/interactive-audit-verification.js
 */

const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
    templatesPath: './web/templates',
    staticJsPath: './web/static/js',
    webAppPath: './web/app.py'
};

// Test results
let results = {
    passed: 0,
    failed: 0,
    issues: []
};

function log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const prefix = {
        info: 'ℹ️',
        pass: '✅',
        fail: '❌',
        warn: '⚠️'
    }[type];

    console.log(`${timestamp} ${prefix} ${message}`);
}

function addIssue(category, file, issue, severity = 'medium') {
    results.issues.push({ category, file, issue, severity });
    results.failed++;
    log(`${file}: ${issue}`, 'fail');
}

function addPass(description) {
    results.passed++;
    log(description, 'pass');
}

// Test 1: Check for duplicate function definitions
function testDuplicateFunctions() {
    log('Testing for duplicate function definitions...');

    const templates = fs.readdirSync(CONFIG.templatesPath)
        .filter(f => f.endsWith('.html'))
        .map(f => path.join(CONFIG.templatesPath, f));

    const functionCounts = {};

    templates.forEach(file => {
        const content = fs.readFileSync(file, 'utf8');
        const functionMatches = content.match(/function\s+(\w+)\s*\(/g);

        if (functionMatches) {
            functionMatches.forEach(match => {
                const funcName = match.match(/function\s+(\w+)/)[1];

                // Skip common patterns that should be duplicated
                if (['createPersona', 'loadConversations'].includes(funcName)) {
                    return;
                }

                if (!functionCounts[funcName]) {
                    functionCounts[funcName] = [];
                }
                functionCounts[funcName].push(path.basename(file));
            });
        }
    });

    // Check for problematic duplicates
    for (const [funcName, files] of Object.entries(functionCounts)) {
        if (files.length > 1) {
            const uniqueFiles = [...new Set(files)];
            if (uniqueFiles.length > 1) {
                addIssue('Duplicate Functions', uniqueFiles.join(', '),
                    `Function '${funcName}' defined in ${uniqueFiles.length} different templates`);
            }
        }
    }

    if (results.issues.filter(i => i.category === 'Duplicate Functions').length === 0) {
        addPass('No problematic duplicate function definitions found');
    }
}

// Test 2: Check for missing function definitions
function testMissingFunctions() {
    log('Testing for missing function definitions...');

    const templates = fs.readdirSync(CONFIG.templatesPath)
        .filter(f => f.endsWith('.html'))
        .map(f => path.join(CONFIG.templatesPath, f));

    // Get shared.js functions
    const sharedJsContent = fs.readFileSync(path.join(CONFIG.staticJsPath, 'shared.js'), 'utf8');
    const sharedFunctions = new Set(
        (sharedJsContent.match(/function\s+(\w+)/g) || [])
            .map(m => m.match(/function\s+(\w+)/)[1])
    );

    templates.forEach(file => {
        const content = fs.readFileSync(file, 'utf8');
        const fileName = path.basename(file);

        // Extract onclick function calls
        const onclickMatches = content.match(/onclick="([^"]+)"/g) || [];
        const templateFunctions = new Set(
            (content.match(/function\s+(\w+)/g) || [])
                .map(m => m.match(/function\s+(\w+)/)[1])
        );

        onclickMatches.forEach(onclick => {
            const funcCalls = onclick.match(/(\w+)\s*\(/g);
            if (funcCalls) {
                funcCalls.forEach(call => {
                    const funcName = call.replace(/\s*\(/, '');

                    // Skip built-in functions and DOM methods
                    const skipFunctions = [
                        'event', 'document', 'window', 'console', 'alert', 'confirm', 'prompt',
                        'stopPropagation', 'preventDefault', 'getElementById', 'querySelector',
                        'requestSubmit', 'classList', 'closest', 'contains', 'toggle', 'add',
                        'remove', 'setAttribute', 'getAttribute', 'focus', 'blur', 'click',
                        'if', 'else', 'this', 'target', 'currentTarget', 'submit', 'reset'
                    ];
                    if (skipFunctions.includes(funcName)) {
                        return;
                    }

                    // Check if function exists
                    if (!templateFunctions.has(funcName) && !sharedFunctions.has(funcName)) {
                        addIssue('Missing Functions', fileName,
                            `Function '${funcName}' called in onclick but not defined`);
                    }
                });
            }
        });
    });

    if (results.issues.filter(i => i.category === 'Missing Functions').length === 0) {
        addPass('All onclick functions are properly defined');
    }
}

// Test 3: Check API endpoint accessibility
function testAPIEndpoints() {
    log('Testing API endpoint definitions...');

    const appPyContent = fs.readFileSync(CONFIG.webAppPath, 'utf8');
    const routes = appPyContent.match(/@app\.route\s*\(\s*['"][^'"]+['"]/g) || [];

    const endpointCount = routes.length;

    if (endpointCount > 60) {
        addPass(`All ${endpointCount} API endpoints defined in app.py`);
    } else {
        addIssue('API Endpoints', 'app.py',
            `Only ${endpointCount} endpoints found, expected 60+`, 'high');
    }

    // Check critical endpoints exist
    const criticalEndpoints = [
        '/api/conversations',
        '/api/conversations/<conversation_id>/star',
        '/login',
        '/logout',
        '/chat'
    ];

    criticalEndpoints.forEach(endpoint => {
        // Create a more flexible pattern for endpoint matching
        let pattern = endpoint.replace(/<[^>]+>/g, '<[^>]+>');
        pattern = pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/<\\[\\^\\>\\]\\+\\>/g, '[^/]+');
        const regex = new RegExp(`@app\\.route\\s*\\(\\s*['"][^'"]*/` + pattern.replace(/^\//, '') + `['"]`);

        if (!regex.test(appPyContent)) {
            addIssue('Missing Endpoints', 'app.py',
                `Critical endpoint '${endpoint}' not found`, 'high');
        }
    });
}

// Test 4: Check form submissions
function testFormSubmissions() {
    log('Testing form submission handlers...');

    const templates = fs.readdirSync(CONFIG.templatesPath)
        .filter(f => f.endsWith('.html'))
        .map(f => path.join(CONFIG.templatesPath, f));

    templates.forEach(file => {
        const content = fs.readFileSync(file, 'utf8');
        const fileName = path.basename(file);

        // Check for onsubmit handlers
        const onsubmitMatches = content.match(/onsubmit="([^"]+)"/g) || [];

        onsubmitMatches.forEach(onsubmit => {
            const funcCall = onsubmit.match(/onsubmit="(\w+)\(/);
            if (funcCall) {
                const funcName = funcCall[1];

                // Check if function exists in template
                if (!content.includes(`function ${funcName}`)) {
                    addIssue('Form Handlers', fileName,
                        `Form submission handler '${funcName}' not defined`);
                }
            }
        });
    });

    if (results.issues.filter(i => i.category === 'Form Handlers').length === 0) {
        addPass('All form submission handlers are properly defined');
    }
}

// Main execution
function runVerification() {
    log('🚀 Starting MV Internal Interactive Element Verification');
    log('================================================');

    testDuplicateFunctions();
    testMissingFunctions();
    testAPIEndpoints();
    testFormSubmissions();

    log('================================================');
    log(`📊 VERIFICATION COMPLETE`);
    log(`✅ Passed: ${results.passed}`);
    log(`❌ Failed: ${results.failed}`);

    if (results.issues.length > 0) {
        log('\n🐛 ISSUES FOUND:');
        results.issues.forEach((issue, i) => {
            log(`${i + 1}. [${issue.severity.toUpperCase()}] ${issue.category} in ${issue.file}`);
            log(`   ${issue.issue}`);
        });

        const highIssues = results.issues.filter(i => i.severity === 'high').length;
        if (highIssues > 0) {
            log(`\n🚨 ${highIssues} HIGH PRIORITY issues require immediate attention!`);
            process.exit(1);
        } else {
            log(`\n⚠️ ${results.issues.length} medium/low priority issues found.`);
        }
    } else {
        log('\n🎉 ALL TESTS PASSED! No issues found.');
    }
}

// Run if called directly
if (require.main === module) {
    runVerification();
}

module.exports = { runVerification };