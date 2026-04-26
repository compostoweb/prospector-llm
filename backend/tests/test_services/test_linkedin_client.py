from services.content.linkedin_client import LinkedInClient, LinkedInClientError


def test_should_ignore_image_asset_poll_error_for_partner_assets_permission() -> None:
    exc = LinkedInClientError(
        403,
        '{"status":403,"serviceErrorCode":100,"code":"ACCESS_DENIED","message":"Not enough permissions to access: partnerApiAssets.GET.20260201"}',
    )

    assert LinkedInClient._should_ignore_image_asset_poll_error(exc) is True


def test_should_not_ignore_other_image_asset_poll_errors() -> None:
    exc = LinkedInClientError(
        403,
        '{"status":403,"serviceErrorCode":100,"code":"ACCESS_DENIED","message":"Not enough permissions to access: somethingElse.GET.20260201"}',
    )

    assert LinkedInClient._should_ignore_image_asset_poll_error(exc) is False
