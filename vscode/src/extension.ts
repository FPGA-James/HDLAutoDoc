import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('hdlAutodoc.showDocumentation', () => {
      void vscode.window.showInformationMessage('HDL AutoDoc: the documentation panel is not built yet.');
    }),
  );
}

export function deactivate(): void {}
