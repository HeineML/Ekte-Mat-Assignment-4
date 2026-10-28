from app.models import get_repos
from app.models.seed import DEMO_ACCOUNTS


def test_seed_command_loads_synthetic_data(app):
    result = app.test_cli_runner().invoke(args=["seed"])
    assert result.exit_code == 0, result.output
    assert "admin@example.test" in result.output

    with app.app_context():
        repos = get_repos()
        users = [repos.users.get_by_email(email) for _, email, _, _ in DEMO_ACCOUNTS]
        assert sum(u.is_admin for u in users) == 1
        for user, (_, _, password, _) in zip(users, DEMO_ACCOUNTS):
            assert user.password_hash != password

        assert len(repos.food.list_categories()) == 5
        assert len(repos.food.list_published()) < len(repos.food.list_all())
        assert len(repos.orders.list_all()) == 3
        assert len(repos.questions.list_all()) == 2
        assert len(repos.questions.list_all(unanswered_only=True)) == 1


def test_seed_can_run_twice(app):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed"]).exit_code == 0
    assert runner.invoke(args=["seed"]).exit_code == 0
    with app.app_context():
        assert len(get_repos().orders.list_all()) == 3


def test_init_db_empties_storage(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed"])
    result = runner.invoke(args=["init-db"])
    assert result.exit_code == 0
    with app.app_context():
        assert get_repos().food.list_all() == []
