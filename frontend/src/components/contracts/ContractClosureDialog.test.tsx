import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ContractClosureDialog from './ContractClosureDialog';

describe('ContractClosureDialog', () => {
  it('disables submit until notes are provided', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();

    render(
      <ContractClosureDialog
        open
        saving={false}
        error={null}
        onClose={vi.fn()}
        onConfirm={onConfirm}
      />,
    );

    const submitButton = screen.getByRole('button', { name: 'Mark as Terminated' });
    expect(submitButton).toBeDisabled();

    await user.type(screen.getByLabelText('Closing notes'), '   ');
    expect(submitButton).toBeDisabled();

    await user.clear(screen.getByLabelText('Closing notes'));
    await user.type(screen.getByLabelText('Closing notes'), '  Cierre acordado  ');
    expect(submitButton).toBeEnabled();

    await user.click(submitButton);
    expect(onConfirm).toHaveBeenCalledWith('Cierre acordado');
  });
});
